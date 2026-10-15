"""Phase 1 step 2: merge detail records into the procedure dataset and normalise fields.

Input : data/procedures_all.csv, raw/details_*.jsonl
Output: data/phase1_projects.csv   in-scope procedures with detail fields (Phase 1 deliverable)
        data/phase1_quality.csv    field completeness summary
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, RAW = ROOT / "data", ROOT / "raw"

def code(v):
    """Detail extracts returned codes either as 'X', 'X|label' or {'code': X}."""
    if v is None:
        return None
    if isinstance(v, dict):
        return v.get("code")
    return str(v).split("|")[0]

recs = []
for f in sorted(RAW.glob("details_*.jsonl")):
    for line in f.read_text().splitlines():
        if line.strip():
            recs.append(json.loads(line))
det = pd.DataFrame(recs)
det["id"] = det["id"].astype(str)
assert det["id"].is_unique, det["id"][det["id"].duplicated()]
for c in ["aankondigingCode", "typeOpdracht", "procedureCode", "euOrNational"]:
    det[c] = det[c].map(code)

def cpv_main(lst):
    for item in lst or []:
        p = item.split("|")
        if len(p) >= 3 and p[2].strip().lower() in ("true", "main"):
            return p[0]
    return (lst or [None])[0].split("|")[0] if lst else None

det["cpv_main"] = det["cpv"].map(cpv_main)
det["cpv_all"] = det["cpv"].map(lambda l: ";".join(x.split("|")[0] for x in (l or []) if not x.startswith("TRUNCATED")))
det["cpv_truncated"] = det["cpv"].map(lambda l: any(x.startswith("TRUNCATED") for x in (l or [])))
det["nuts_codes"] = det["nuts"].map(lambda l: ";".join(x.split("|")[0] for x in (l or [])))
det["nuts_labels"] = det["nuts"].map(lambda l: ";".join(x.split("|")[1] for x in (l or []) if "|" in x))
det["keywords"] = det["keywords"].map(lambda l: ";".join(l) if isinstance(l, list) else None)
det["value_stated"] = det["valueStated"].map(lambda l: " / ".join(l) if isinstance(l, list) else l)
for c in ["publicatieDatum", "sluitingsDatum", "aanvang", "voltooiing"]:
    det[c] = det[c].map(lambda s: s[:10] if isinstance(s, str) and re.match(r"\d{4}-\d{2}-\d{2}", s) else None)

keep = {
    "id": "detail_notice_id", "kenmerk": "kenmerk", "referentieNummer": "reference_number",
    "pbNummerTed": "ted_publication_number", "aankondigingCode": "detail_notice_type",
    "procedureCode": "detail_procedure", "euOrNational": "eu_or_national",
    "sluitingsDatum": "detail_closing_date", "aanvang": "contract_start", "voltooiing": "contract_end",
    "cpv_main": "cpv_main", "cpv_all": "cpv_all", "cpv_truncated": "cpv_truncated",
    "nuts_codes": "nuts_codes", "nuts_labels": "nuts_labels", "keywords": "keywords",
    "isGegund": "is_awarded", "afgerond": "is_completed_procedure",
    "vroegtijdigBeeindigd": "is_terminated_early", "value_stated": "value_stated_in_description",
    "durationStated": "duration_stated", "summary": "scope_summary_ai",
}
det = det[list(keep)].rename(columns=keep)

procs = pd.read_csv(DATA / "procedures_all.csv", dtype=str)
procs = procs[procs["in_scope"] == "True"].copy()
m = procs.merge(det, left_on="latest_notice_id", right_on="detail_notice_id", how="left", indicator=True)
missing = m[m["_merge"] != "both"]
assert missing.empty, missing[["procedure_key", "latest_notice_id"]]
m = m.drop(columns=["_merge"])

# consistency check: listing type vs detail type for the same notice
m["type_check"] = (m["latest_notice_type"] == m["detail_notice_type"]).map({True: "ok", False: "MISMATCH"})

# ---- location ---------------------------------------------------------------
NUTS2_PROVINCE = {
    "NL11": "Groningen", "NL12": "Friesland", "NL13": "Drenthe", "NL21": "Overijssel",
    "NL22": "Gelderland", "NL23": "Flevoland", "NL32": "Noord-Holland", "NL33": "Zuid-Holland",
    "NL34": "Zeeland", "NL35": "Utrecht", "NL36": "Zuid-Holland", "NL41": "Noord-Brabant",
    "NL42": "Limburg",
}
def province_from_nuts(codes):
    provs = sorted({NUTS2_PROVINCE[c[:4]] for c in (codes or "").split(";") if len(c) >= 4 and c[:4] in NUTS2_PROVINCE})
    return ";".join(provs) or None

# Reviewer-coded province for authorities whose seat is unambiguous. Used only when the
# notice's own NUTS code is national ("NL") or a NUTS1 macro-region.
AUTHORITY_PROVINCE = {
    "Gemeente Amstelveen": "Noord-Holland", "Gemeente Amsterdam": "Noord-Holland",
    "Gemeente Amsterdam, Ingenieursbureau": "Noord-Holland",
    "Gemeente Amsterdam, Uitvoeringsorganisatie Infrastructuur en Energie": "Noord-Holland",
    "GVB Infra B.V.": "Noord-Holland", "Gemeente Enschede": "Overijssel", "Gemeente Ede": "Gelderland",
    "Gemeente Amersfoort": "Utrecht", "Gemeente Zwijndrecht": "Zuid-Holland",
    "Waterschap Rivierenland": "Gelderland", "Provincie Overijssel": "Overijssel",
    "Provincie Utrecht": "Utrecht", "Gemeente Haarlem": "Noord-Holland", "Gemeente Arnhem": "Gelderland",
    "Provincie Limburg": "Limburg", "Provincie Noord-Brabant": "Noord-Brabant",
    "provincie Noord-Holland": "Noord-Holland", "Provincie Noord-Holland": "Noord-Holland",
    "WarmteStad BV": "Groningen", "Gemeente Rotterdam": "Zuid-Holland", "R.E.T. N.V.": "Zuid-Holland",
    "Havenbedrijf Rotterdam": "Zuid-Holland", "Gemeente Maashorst": "Noord-Brabant",
    "Gemeente Zaanstad": "Noord-Holland", "gemeente 's-Hertogenbosch": "Noord-Brabant",
    "Gemeente Houten": "Utrecht", "Gemeente Súdwest-Fryslân": "Friesland",
    "Gemeente Gooise Meren": "Noord-Holland", "Wetterskip Fryslân": "Friesland",
    "Waterschap Hunze en Aa's": "Groningen;Drenthe", "Gemeente Tilburg": "Noord-Brabant",
    "Provincie Flevoland": "Flevoland", "Gemeente Leiden": "Zuid-Holland", "Gemeente Woerden": "Utrecht",
    "Provincie Gelderland": "Gelderland", "Gemeente Den Haag": "Zuid-Holland",
    "Gemeente Maassluis": "Zuid-Holland", "Stadswerk 072 N.V.": "Noord-Holland",
    "Gemeente Den Helder": "Noord-Holland", "Provincie Groningen": "Groningen",
    "Provincie Zuid-Holland": "Zuid-Holland", "Gemeente Almere": "Flevoland",
    "Gemeente Almelo": "Overijssel", "Gemeente Pekela": "Groningen", "Gemeente Opsterland": "Friesland",
    "Gemeente Maastricht": "Limburg", "Gemeente Delft": "Zuid-Holland",
    "Gemeente Leidschendam-Voorburg": "Zuid-Holland", "Gemeente Pijnacker-Nootdorp": "Zuid-Holland",
    "Hoogheemraadschap van Schieland en de Krimpenerwaard": "Zuid-Holland",
    "Groningen Seaports N.V.": "Groningen", "Hoogheemraadschap van Rijnland": "Zuid-Holland;Noord-Holland",
    "Waterschap Brabantse Delta": "Noord-Brabant", "Evides N.V.": "Zeeland;Zuid-Holland",
    "Waterschap Aa en Maas": "Noord-Brabant", "Hoogheemraadschap van Delfland": "Zuid-Holland",
    "Waterschap Vallei en Veluwe": "Gelderland", "Waterschap Hollandse Delta": "Zuid-Holland",
    "Gemeente Groningen, Afdeling Stadsingenieurs": "Groningen", "Stichting Waternet": "Noord-Holland",
    "Waterschap Scheldestromen": "Zeeland", "N.V. Waterbedrijf Groningen": "Groningen",
    "Waterschap Zuiderzeeland": "Flevoland", "Waterschap Noorderzijlvest": "Groningen",
    "Hoogheemraadschap Hollands Noorderkwartier": "Noord-Holland", "Gemeente Middelburg": "Zeeland",
    "Gemeente Eindhoven": "Noord-Brabant", "Gemeente Heusden": "Noord-Brabant",
    "Gemeente Leeuwarden": "Friesland", "Gemeente Hardenberg": "Overijssel",
    "Schiphol Nederland B.V.": "Noord-Holland", "GEM Crailo B.V.": "Noord-Holland",
    "Warmtebedrijf Muiderberg B.V.": "Noord-Holland", "N.V. HVC": None, "Vattenfall": None,
}
# Place names stated in the notice title/description (reviewer-coded), keyed by notice id.
TITLE_LOCATION = {
    "426872": "Noord-Brabant",            # MV network Vliegbasis Eindhoven
    "443608": "Utrecht;Zuid-Holland;Noord-Brabant",  # A27 Everdingen-Hooipolder (Gorinchem, Geertruidenberg)
    "411670": "Zuid-Holland",             # Haringvlietsluizen
    "430965": "Limburg",                  # weirs Linne, Roermond, Belfeld, Sambeek
    "430194": "Overijssel",               # Spooldersluis Zwolle
    "436212": "Groningen",                # Eemsgeul / Eemshaven
    "443508": "Overijssel;Gelderland;Utrecht",  # KRW Oost: IJssel, Zwarte Water, Nederrijn/Lek
    "426200": "Limburg;Noord-Brabant",    # KRW 7 Meuse
    "424166": "Gelderland;Overijssel",    # Vaarwegen Oost Nederland
    "430477": "Noord-Holland",            # OS IJmuiden - OS Velsen
    "414131": "Zuid-Holland",             # ProRail 4 bridges Zuid-Holland
    "436451": "Zuid-Holland;Utrecht;Zeeland",  # Stedin lots: Den Haag/Utrecht and Rotterdam/Zeeland
    "424587": "Zeeland;Noord-Holland",    # nourishment Westkapelle, Breezand
}
def location(row):
    p = province_from_nuts(row["nuts_codes"])
    if p:
        return pd.Series({"province": p, "location_source": "notice NUTS code"})
    if row["latest_notice_id"] in TITLE_LOCATION:
        return pd.Series({"province": TITLE_LOCATION[row["latest_notice_id"]],
                          "location_source": "place named in notice (reviewer-coded)"})
    a = AUTHORITY_PROVINCE.get(row["authority"])
    if a:
        return pd.Series({"province": a, "location_source": "authority seat (reviewer-coded)"})
    return pd.Series({"province": None, "location_source": "national/multi-region or unknown"})

m = pd.concat([m, m.apply(location, axis=1)], axis=1)
m["nuts_granularity"] = m["nuts_codes"].map(
    lambda s: max((len(c) for c in (s or "").split(";")), default=0)).map(
    {2: "national", 3: "NUTS1", 4: "NUTS2", 5: "NUTS3"}).fillna("none")

# ---- procurement status (from the latest notice) ------------------------------
def status(row):
    # A rectification (REC) inherits the stage of the notice it corrects: use the latest
    # non-REC notice of the procedure.
    types = [x for x in str(row["notice_types"]).split(";") if x and x != "REC"]
    t = types[-1] if types else row["latest_notice_type"]
    closing = row["closing_date"] if isinstance(row["closing_date"], str) else ""
    title, summ = row["title"], str(row["scope_summary_ai"])
    if str(row["is_terminated_early"]) == "True" or row["latest_notice_type"] == "VBE":
        return "terminated"
    if re.search(r"vooraankondiging|marktconsultatie|marktverkenning|marktconsulatie|market consultation|marktinformatie", title, re.I):
        return "pre-tender (market consultation / prior information)"
    if re.search(r"erkenningsregeling|qualification system", title, re.I):
        if re.search(r"beëindiging|terminat|ends qualification", title + " " + summ, re.I):
            return "terminated"
        return "qualification system open (continuous)"
    if t in ("MAC", "VAK"):
        return "pre-tender (market consultation / prior information)"
    if t in ("AAO", "REC"):
        return "tendering" if closing >= "2026-10-15" else "tender closed, award pending"
    if t == "AGO":
        return "awarded"
    if t == "AAW":
        return "in delivery (contract modified)"
    return "unknown"
m["procurement_status"] = m.apply(status, axis=1)

cols = ["procedure_key", "title", "authority", "strata", "procurement_status", "latest_notice_type",
        "most_advanced_type", "n_notices_2026", "first_notice_2026", "latest_notice_2026", "closing_date",
        "contract_start", "contract_end", "contract_type", "procedure_code", "eu_or_national",
        "cpv_main", "cpv_all", "cpv_truncated", "nuts_codes", "nuts_labels", "nuts_granularity",
        "province", "location_source", "keywords", "value_stated_in_description", "duration_stated",
        "scope_summary_ai", "gist", "reference_number", "kenmerk", "ted_publication_number",
        "notice_ids", "latest_notice_id", "source_url", "type_check", "validation_flags"]
out = m[cols].sort_values(["strata", "authority", "title"])
out.to_csv(DATA / "phase1_projects.csv", index=False)

q = pd.DataFrame({
    "field": cols,
    "non_missing": [out[c].notna().sum() for c in cols],
})
q["pct"] = (100 * q["non_missing"] / len(out)).round(1)
q.to_csv(DATA / "phase1_quality.csv", index=False)

print(f"procedures: {len(out)}; type mismatches: {(out['type_check']=='MISMATCH').sum()}")
print(out["procurement_status"].value_counts().to_string())
print(out["nuts_granularity"].value_counts().to_string())
print(out["location_source"].value_counts().to_string())
print("value stated:", out["value_stated_in_description"].notna().sum(), "| TED number:", out["ted_publication_number"].notna().sum())
