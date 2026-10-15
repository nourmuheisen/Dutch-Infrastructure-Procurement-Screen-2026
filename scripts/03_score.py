"""Phase 2: transparent rule-based CP&I relevance scoring.

Every point awarded is traceable to a named signal that matched observable text or a
structured field of the notice. Reviewer adjustments (data/review_adjustments.csv) are
applied on top and recorded separately, so rule scores and reviewed scores can be compared.

Input : data/phase1_projects.csv, scripts/scoring_config.json, data/review_adjustments.csv (optional)
Output: data/phase2_scores.csv
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((ROOT / "scripts" / "scoring_config.json").read_text())

df = pd.read_csv(DATA / "phase1_projects.csv", dtype=str).fillna("")

# --- text preparation ---------------------------------------------------------
NEG = re.compile(r"\b(no|not|unstated|unspecified|neither|nor|without)\b", re.I)
def positive_sentences(text: str) -> str:
    """Drop sentences that only report absence ("PM services are not mentioned")."""
    parts = re.split(r"(?<=[.;])\s+", text)
    return " ".join(p for p in parts if not NEG.search(p))

def corpus(r) -> str:
    return " ".join([r["title"], r["gist"], positive_sentences(r["scope_summary_ai"]),
                     r["keywords"], r["duration_stated"], r["value_stated_in_description"]]).lower()

df["_text"] = df.apply(corpus, axis=1)

# --- signal definitions: (name, weight, test) --------------------------------------
def rx(pattern):
    c = re.compile(pattern, re.I)
    return lambda r: bool(c.search(r["_text"]))

def field(col, values):
    return lambda r: any(v in r[col].split(";") for v in values)

def years(r):
    try:
        return (pd.Timestamp(r["contract_end"]) - pd.Timestamp(r["contract_start"])).days / 365.25
    except Exception:
        return 0

SIGNALS = {
    "investment_planning": [
        ("early market engagement (consultation / prior information)", 1.0,
         lambda r: r["latest_notice_type"] in ("MAC", "VAK") or "MAC" in r["notice_types"].split(";")
         if "notice_types" in r else r["latest_notice_type"] in ("MAC", "VAK")),
        ("feasibility, concept or business-case work", 1.5,
         rx(r"feasib|haalbaar|business case|concept select|concept design|concept level|sketch|schets|no preliminary design|before any preliminary design|alternatives stud|preferred decision|voorkeursbeslissing")),
        ("feasibility/advisory CPV (71241000)", 1.0, lambda r: "71241000" in r["cpv_all"]),
        ("scope or later phase not yet committed", 1.0,
         rx(r"optional|uncertain|if negotiations succeed|if (both )?parties agree|budget approval|business case is approved|may follow|possible tender|planned tender|intends? to|undecided")),
        ("funding or subsidy condition", 0.5, rx(r"subsid|financ|budget|ceiling")),
        ("end-of-life / replace-or-renovate decision", 0.5,
         rx(r"end of (their |its )?(technical )?life|end-of-life|until full replacement|no longer suits|reached the end")),
        ("programme or portfolio of projects", 0.5, rx(r"programm?e|portfolio|subprojects|several projects|multiple projects")),
        ("strategic energy-transition investment", 0.5,
         rx(r"hydrogen|waterstof|heat transition|warmtetransitie|energy transition|energietransitie|grid expansion|scale (up )?district heating|rapidly scale")),
    ],
    "procurement_commercial": [
        ("competitive dialogue", 1.0, field("procedure_code", ["CCD"])),
        ("negotiated procedure", 0.5, field("procedure_code", ["OMB", "OZB", "OHP"])),
        ("bouwteam / two-phase contracting", 1.0,
         rx(r"bouwteam|build[- ]team|design[- ]build team|design-and-build team|two-phase|twee-fasen|first right|exclusive (realisation )?price")),
        ("integrated contract form (DBFM, DBMO, concession, D&C, E&C)", 1.0,
         rx(r"dbfm|dbmo|concession|concessie|uav-?gc|design[- ]and[- ]construct|engineering (and|&) construct")),
        ("framework, lots or qualification system", 0.5,
         rx(r"framework|raamovereenkomst|\blots?\b|percelen|qualification|erkenningsregeling|dynamic purchasing")),
        ("contracting strategy under design", 1.5,
         rx(r"contractor strategy|aannemersstrategie|contracting strategy|collaboration models|procurement strategy|procurement, contracting|views on contracting|feedback on .*contract|tender plan|procurement planning")),
        ("procurement difficulty (termination, re-tender, no bids, withdrawn)", 1.0,
         lambda r: r["procurement_status"] == "terminated" or bool(re.search(
             r"cancel|withdrawn|re-tender|retender|heraanbesteding|no bids|terminated|early termination", r["_text"]))
         or "VBE" in r["notice_types"].split(";")),
        ("contract value or ceiling change", 0.5, rx(r"maximum value|ceiling|increase")),
        ("independent price / cost review", 0.5, rx(r"price review|cost estimate|ssk|kostenraming|cost expertise|kostendeskund")),
    ],
    "controls_assurance": [
        ("three or more technical disciplines", 1.5,
         lambda r: sum(bool(re.search(p, r["_text"])) for p in [
             r"civil|civiel", r"mechanic|werktuig|hydraulic", r"electric|elektro|e&i|low[- ]voltage|medium[- ]voltage",
             r"control system|besturing|automation|3b|operating and control|scada"]) >= 3),
        ("two technical disciplines", 0.5,
         lambda r: sum(bool(re.search(p, r["_text"])) for p in [
             r"civil|civiel", r"mechanic|werktuig|hydraulic", r"electric|elektro|e&i|low[- ]voltage|medium[- ]voltage",
             r"control system|besturing|automation|3b|operating and control|scada"]) == 2),
        ("works under live operation", 1.0,
         rx(r"stays open|kept open|remain open|limit closures|traffic diversion|during (the )?works|while keeping|during realisation")),
        ("interfaces with other contractors, utilities or packages", 1.0,
         rx(r"coordinat|interface|other contractors|third-party|kabels en leidingen|utilit|interdependenc|stakeholder")),
        ("multi-contract programme or multi-site delivery", 0.5,
         rx(r"programm?e|portfolio|fourth contract|clusters|several sites|multiple sites|\d+ sites|three locations|nine .*lots")),
        ("delivery horizon of four years or more", 0.5, lambda r: years(r) >= 4),
        ("hard external deadline", 0.5, rx(r"deadline|by end|by 1 july|december 20\d\d|timetable|service frequency|subsidy")),
        ("scope change on a running major contract", 0.5,
         lambda r: r["latest_notice_type"] == "AAW" and r["procedure_code"] in ("CCD", "NOP")),
        ("programme controls explicitly in scope", 1.5, rx(r"integrated schedule|risk register|programme controls|project controls|integration manager|reporting")),
    ],
    "asset_lifecycle": [
        ("renovation, replacement or overhaul", 1.0, rx(r"renovat|replac|vervang|overhaul|revis|refurbish|renew")),
        ("life-extension decision", 1.5,
         rx(r"life[- ]extend|life-extension|lifespan|levensduur|\blvo\b|until 20[34]\d|more years|end of (their |its )?(technical )?life|until full replacement")),
        ("maintenance or use phase in contract", 1.0,
         rx(r"maintenance|maintain|onderhoud|instandhouding|use phase|upkeep|prestatiecontract|performance contract")),
        ("asset information, inspection or condition data", 1.0,
         rx(r"asset data|asset[- ]management|condition|inspection|inspectie|areaal|arcgis|nen 2767|maintenance plan|monitoring")),
        ("critical or complex asset type", 0.5,
         rx(r"barrier|kering|tunnel|lock|sluis|sluice|movable|beweegbare|bascule|weir|stuw|substation|dike|dijk")),
    ],
}

def score_row(r, signals):
    fired = [(name, w) for name, w, test in signals if test(r)]
    return min(5.0, 1.0 + sum(w for _, w in fired)), "; ".join(f"{n} (+{w})" for n, w in fired)

df["notice_types"] = df["notice_ids"].map(lambda _: "")  # placeholder, replaced below
procs = pd.read_csv(DATA / "procedures_all.csv", dtype=str).set_index("procedure_key")["notice_types"]
df["notice_types"] = df["procedure_key"].map(procs).fillna("")

for cap, sigs in SIGNALS.items():
    res = df.apply(lambda r: score_row(r, sigs), axis=1, result_type="expand")
    df[f"{cap}_rule"], df[f"{cap}_evidence"] = res[0], res[1]

# --- evidence confidence ------------------------------------------------------------
THIN = re.compile(r"only (repeats|refers|points)|placeholder|only a title|repeats only|title only|just the title|only the title|refers readers|points to the tender guide|only to the tender guide|only refers", re.I)
def confidence(r):
    s, why = 1.0, []
    if r["scope_summary_ai"] and not THIN.search(r["scope_summary_ai"]):
        s += 1.5; why.append("substantive description")
    else:
        why.append("description thin or absent")
    if r["nuts_granularity"] in ("NUTS3", "NUTS2"):
        s += 1.0; why.append(f"location from {r['nuts_granularity']}")
    elif r["province"]:
        s += 0.5; why.append("location reviewer-coded")
    else:
        why.append("no sub-national location")
    if len([c for c in r["cpv_all"].split(";") if c]) >= 2:
        s += 0.5; why.append("multiple CPV codes")
    if r["keywords"]:
        s += 0.5; why.append("keywords present")
    if int(r["n_notices_2026"] or 1) >= 2:
        s += 0.5; why.append("several notices in 2026")
    return pd.Series({"confidence": min(5.0, s), "confidence_basis": "; ".join(why)})
df = pd.concat([df, df.apply(confidence, axis=1)], axis=1)

# --- timing and commercial position --------------------------------------------------
ADVISORY_CPV = re.compile(r"^(71[2-5]|72224|79(4|9))")
df["is_advisory_service"] = df.apply(
    lambda r: r["contract_type"].startswith("D") and bool(ADVISORY_CPV.match(r["cpv_main"] or "")), axis=1)

TIMING = {
    "pre-tender (market consultation / prior information)": (5, "strategy and scope still open"),
    "terminated": (4, "re-procurement likely; strategy needs rework"),
    "tendering": (3, "works procurement live; client-side advisers usually already engaged"),
    "qualification system open (continuous)": (3, "contractor pool being built; call-off contracts follow over several years"),
    "tender closed, award pending": (3, "award imminent; delivery set-up starting"),
    "awarded": (2, "contract awarded; controls/assurance during delivery only"),
    "in delivery (contract modified)": (2, "long-running contract; change and claims management only"),
}
df["timing_score"] = df["procurement_status"].map(lambda s: TIMING.get(s, (1, ""))[0]).astype(float)
df["timing_note"] = df["procurement_status"].map(lambda s: TIMING.get(s, (1, "unknown"))[1])

def advisory_position(r):
    notes = []
    if r["is_advisory_service"]:
        if r["procurement_status"] in ("awarded", "in delivery (contract modified)"):
            notes.append("ADVISORY ALREADY AWARDED in this procedure")
        elif r["procurement_status"] == "terminated":
            notes.append("advisory procurement terminated")
        else:
            notes.append("advisory procurement in progress (direct bid route, not a hypothetical need)")
    if r["authority"].startswith("Rijkswaterstaat"):
        notes.append("RWS: project/contract-control advice routed via SROK PPB 2 framework (PwC is a framework party since Jul 2025)")
    return "; ".join(notes)
df["advisory_position"] = df.apply(advisory_position, axis=1)

# --- reviewer adjustments ------------------------------------------------------------
CAPS = list(SIGNALS)
for cap in CAPS:
    df[cap] = df[f"{cap}_rule"]
df["review_note"] = ""
adj_path = DATA / "review_adjustments.csv"
if adj_path.exists():
    adj = pd.read_csv(adj_path, dtype=str)
    for _, a in adj.iterrows():
        mask = df["procedure_key"] == a["procedure_key"]
        assert mask.sum() == 1, f"adjustment key not found: {a['procedure_key']}"
        df.loc[mask, a["capability"]] = float(a["reviewed_score"])
        df.loc[mask, "review_note"] = (df.loc[mask, "review_note"] + f"{a['capability']}: {a['rule_score']}→{a['reviewed_score']} ({a['rationale']}). ")

# --- composite ------------------------------------------------------------------------
w = CFG["capability_weights"]
assert abs(sum(w.values()) - 1) < 1e-9
df["relevance_1to5"] = sum(df[c] * w[c] for c in CAPS)
to100 = lambda s: (s - 1) / 4 * 100
df["relevance_0to100"] = to100(df["relevance_1to5"]).round(1)
# Priority = relevance, modulated by timing and evidence confidence. Multiplicative on purpose:
# an open window or a well-documented notice cannot make an irrelevant project a priority.
# Each modifier scales relevance between (1 - weight) and 1.0.
mt, mc = CFG["priority_modifiers"]["timing"], CFG["priority_modifiers"]["confidence"]
df["timing_factor"] = 1 - mt + mt * (df["timing_score"] - 1) / 4
df["confidence_factor"] = 1 - mc + mc * (df["confidence"] - 1) / 4
df["priority_0to100"] = (df["relevance_0to100"] * df["timing_factor"] * df["confidence_factor"]).round(1)
df = df.sort_values(["priority_0to100", "relevance_0to100"], ascending=False)
df["priority_rank"] = range(1, len(df) + 1)

out_cols = (["priority_rank", "procedure_key", "title", "authority", "strata", "province", "procurement_status",
             "priority_0to100", "relevance_0to100"] + CAPS + ["confidence", "timing_score",
             "advisory_position", "timing_note", "confidence_basis", "review_note"]
            + [f"{c}_rule" for c in CAPS] + [f"{c}_evidence" for c in CAPS]
            + ["is_advisory_service", "scope_summary_ai", "cpv_main", "nuts_codes", "latest_notice_id", "source_url"])
df[out_cols].to_csv(DATA / "phase2_scores.csv", index=False)
print(df[["priority_rank", "priority_0to100", "relevance_0to100"] + CAPS + ["confidence", "timing_score", "title"]]
      .head(40).to_string(max_colwidth=60))
print("\nscore distribution:\n", df[CAPS].describe().round(2).to_string())
