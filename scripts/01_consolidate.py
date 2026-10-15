"""Phase 1 step 1: consolidate raw TenderNed listing extracts.

Input : raw/listings_*.tsv  (rows extracted from the TenderNed public API listing
        endpoint via the web-fetch tool, one file per sector stratum)
Output: data/notices_all.csv       one row per unique publicatieId (notice)
        data/procedures_all.csv    one row per procedure (notices grouped)
        data/screening_log.csv     why each procedure was kept or excluded
"""
import re, unicodedata
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "raw", ROOT / "data"
DATA.mkdir(exist_ok=True)

STRATUM = {
    # energy
    "45231400-9": "energy", "45251000-2": "energy", "45232140-2": "energy",
    "45232200-4": "energy", "09332000-5": "energy",
    # transport
    "45233120-6": "transport", "45234100-7": "transport",
    "45221000-2": "transport", "45241000-1": "transport",
    # water
    "45240000-1": "water", "45246000-3": "water", "45252000-3": "water",
    "45246400-7": "water",
    # renewal / building refurbishment
    "45453000-7": "renewal",
    # advisory & engineering services
    "71541000-2": "advisory", "71241000-9": "advisory", "71311000-1": "advisory",
    "71242000-6": "advisory", "79421000-1": "advisory", "79411000-8": "advisory",
}

NOTICE_TYPES = {
    "VAK": "prior information", "MAC": "market consultation",
    "AAO": "contract notice", "REC": "rectification",
    "AGO": "award notice", "AAW": "contract modification",
    "VBE": "early termination",
}

frames = []
for f in sorted(RAW.glob("listings_*.tsv")):
    df = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False)
    df["source_file"] = f.name
    frames.append(df)
raw = pd.concat(frames, ignore_index=True)
raw = raw.replace({"NA": None, "": None})
raw["stratum"] = raw["query_cpv"].map(STRATUM)
assert raw["stratum"].notna().all(), raw.loc[raw["stratum"].isna(), "query_cpv"].unique()
print(f"raw rows: {len(raw)} from {raw['source_file'].nunique()} files")

# basic validity checks on transcribed identifiers
bad_id = ~raw["publicatieId"].str.fullmatch(r"\d{6}")
assert not bad_id.any(), raw.loc[bad_id, "publicatieId"]
raw["publicatieDatum"] = pd.to_datetime(raw["publicatieDatum"])
assert raw["publicatieDatum"].dt.year.eq(2026).all()

# ---- notice level: one row per publicatieId; keep every stratum it was found in
agg = (raw.sort_values("query_cpv")
          .groupby("publicatieId")
          .agg(strata=("stratum", lambda s: ";".join(sorted(set(s)))),
               query_cpvs=("query_cpv", lambda s: ";".join(sorted(set(s)))),
               n_hits=("query_cpv", "size")))
notices = raw.drop_duplicates("publicatieId").set_index("publicatieId")
notices = notices.drop(columns=["query_cpv", "stratum", "source_file"]).join(agg).reset_index()
notices["notice_type"] = notices["typePublicatie"].map(NOTICE_TYPES).fillna("other")
notices["source_url"] = "https://www.tenderned.nl/aankondigingen/overzicht/" + notices["publicatieId"]
print(f"unique notices: {len(notices)} (duplicate hits removed: {len(raw) - len(notices)})")

# ---- procedure key ---------------------------------------------------------
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(\d+\)$", "", s.strip())          # trailing "(2)" re-tender marker kept separately
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def proc_key(row) -> str:
    t = row["aanbestedingNaam"] or ""
    m = re.match(r"\s*(31\d{6})", t)                 # Rijkswaterstaat 8-digit project number
    if m:
        return f"RWS-{m.group(1)}"
    auth = norm(row["opdrachtgeverNaam"]).replace("rijkswaterstaat programma s projecten en onderhoud", "rws ppo")
    title = norm(t)
    # notices of one procedure differ only by prefixes such as "Aankondiging Vrijwillige transparantie"
    title = re.sub(r"^(aankondiging (van )?(een )?)?(vrijwillige transparantie )", "", title)
    return f"{auth}|{title}"

notices["procedure_key"] = notices.apply(proc_key, axis=1)
# Manual grouping of notices whose titles vary across one procedure. Each was checked by
# hand: same authority, same scope description, sequential publication dates.
MANUAL_GROUPS = {
    "stedin|hs trace werkzaamheden": ["436451", "435076", "419174", "415097"],
    "ret|raamovereenkomst laswerkzaamheden tramspoor": ["425341", "424506"],
    "den haag|inthr lijn 6 en lijn 12": ["436744", "415379", "415228", "409545"],
    "enschede|ingenieursdiensten pathmos stadsveld": ["437704", "435825", "429013"],
}
for key, ids in MANUAL_GROUPS.items():
    notices.loc[notices["publicatieId"].isin(ids), "procedure_key"] = "MANUAL-" + key
# Flag for validation: 443330 carries RWS number 31003668 (Coentunnel DBFM) but an
# A9 Gaasperdammerweg title, so its grouping depends on the source record.
notices["validation_flag"] = notices["publicatieId"].eq("443330").map(
    {True: "title/number mismatch: check source", False: None})
type_rank = {"AGO": 6, "AAW": 5, "VBE": 5, "AAO": 4, "REC": 3, "VAK": 2, "MAC": 1}
notices["type_rank"] = notices["typePublicatie"].map(type_rank).fillna(0)

def summarise(g: pd.DataFrame) -> pd.Series:
    g = g.sort_values("publicatieDatum")
    latest = g.iloc[-1]
    most_advanced = g.sort_values(["type_rank", "publicatieDatum"]).iloc[-1]
    return pd.Series({
        "title": latest["aanbestedingNaam"],
        "authority": latest["opdrachtgeverNaam"],
        "strata": ";".join(sorted(set(";".join(g["strata"]).split(";")))),
        "contract_type": ";".join(sorted(set(g["typeOpdracht"].dropna()))),
        "procedure_code": ";".join(sorted(set(g["procedure"].dropna()))),
        "european": ";".join(sorted(set(g["europees"].dropna()))),
        "n_notices_2026": len(g),
        "notice_types": ";".join(g["typePublicatie"]),
        "first_notice_2026": g["publicatieDatum"].min().date(),
        "latest_notice_2026": g["publicatieDatum"].max().date(),
        "latest_notice_type": latest["typePublicatie"],
        "most_advanced_type": most_advanced["typePublicatie"],
        "closing_date": max([d for d in g["sluitingsDatum"].dropna()], default=None),
        "gist": latest["gist"] or g["gist"].dropna().iloc[-1] if g["gist"].notna().any() else None,
        "notice_ids": ";".join(g["publicatieId"]),
        "validation_flags": ";".join(g["validation_flag"].dropna()) or None,
        "latest_notice_id": latest["publicatieId"],
        "source_url": latest["source_url"],
    })

procs = notices.groupby("procedure_key").apply(summarise, include_groups=False).reset_index()
print(f"procedures: {len(procs)}")

# ---- infrastructure screen (rule-based, documented) -------------------------
# Exclude procedures whose object is a social/real-estate building or non-infrastructure service.
EXCLUDE_TERMS = [
    r"\bschool\b", r"lyceum", r"college\b", r"\bikc\b", r"onderwijs", r"campus", r"zwembad",
    r"sporthal", r"theater", r"lievekamp", r"gemeentehuis", r"cultureel centrum", r"nme gebouw",
    r"umc\b", r"ziekenhuis", r"huisvesting", r"kitchen|keuken", r"nitrogen|stikstof",
    r"omgevingsplan", r"energieloket", r"thermal spray", r"opvaardokken", r"nuclear security",
    r"tribunebelasting", r"verkeerstellingen", r"deel m", r"ict", r"dutchtechzone",
    r"economische adviesdiensten", r"innovatie en adviesdiensten", r"ho chi minh",
    r"rivierkreeften", r"loonwerk", r"parkeergarage", r"hoogbouw", r"woningbouw",
    r"amsteleind", r"fellingen", r"braassemerland", r"woonrijp", r"external professionals",
    r"seb controles", r"ondersteuning omgevingsmanagement gevelisolatie", r"dris",
    r"strategisch advies en begeleiden tenderprocedures", r"adviesdiensten fysiek domein",
    r"oefenterrein", r"geluidsscherm", r"stationsgebied", r"vergunningsdiensten",
    r"financieel en administratief", r"nen 2767", r"herinrichting", r"wijkvernieuwing",
    r"reconstructie vliegeniersbuurt", r"vrijliggend fietspad", r"veiliger maken",
    r"snelle fietsroute", r"groene loper", r"landpark", r"logistieke hub", r"conservering bruggen",
    r"rioolvervanging", r"riolering polderweg", r"programma van eisen", r"terminal",
    r"operationele gebouwen", r"vliegtuigafhandeling", r"daken", r"stalen masten",
    # added after manual review of the first screening pass
    r"groene wellen", r"outdoor pool", r"transcomplex", r"hoofdkantoor", r"herinrichten",
    r"mki w", r"zonnescans",
]
exclude_re = re.compile("|".join(EXCLUDE_TERMS))
# Authorities whose 2026 procurement in this sample is housing/building programmes, not infra
EXCLUDE_AUTHORITIES = {"nationaal coordinator groningen": "housing reinforcement programme (NCG), not infrastructure"}

def screen(row):
    auth = norm(row["authority"])
    if auth in EXCLUDE_AUTHORITIES:
        return pd.Series({"in_scope": False, "screen_reason": "excluded: " + EXCLUDE_AUTHORITIES[auth]})
    text = norm(f"{row['title']} {row['gist'] or ''}")
    m = exclude_re.search(text)
    if m:
        return pd.Series({"in_scope": False, "screen_reason": f"excluded: matched '{m.group(0)}'"})
    return pd.Series({"in_scope": True, "screen_reason": "kept: infrastructure object or infra-owner advisory"})

procs = pd.concat([procs, procs.apply(screen, axis=1)], axis=1)
procs = procs.sort_values(["in_scope", "strata", "latest_notice_2026"], ascending=[False, True, False])

notices.drop(columns=["type_rank"]).to_csv(DATA / "notices_all.csv", index=False)
procs.to_csv(DATA / "procedures_all.csv", index=False)
procs[["procedure_key", "title", "authority", "strata", "in_scope", "screen_reason"]].to_csv(
    DATA / "screening_log.csv", index=False)

kept = procs[procs["in_scope"]]
print(f"in scope: {len(kept)} procedures covering {kept['n_notices_2026'].sum()} notices")
print(kept["strata"].value_counts().to_string())
print(kept["most_advanced_type"].value_counts().to_string())
