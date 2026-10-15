"""Phase 3: delivery exposure assessment.

Two parts, kept separate from CP&I relevance:

A. Grid materiality - is electricity network capacity materially relevant to delivering
   this project? Classified from the project's own scope. No congestion figures are
   used: the Netbeheer Nederland capacity-map exports were not retrievable from this
   environment, and the notices do not locate projects precisely enough to link them
   (see reports/phase3_constraints.md).

B. Other delivery-exposure signals evidenced in the notices themselves (procurement
   market response, live-operation constraints, hard external deadlines, owner-side
   integration of many packages, single-supplier dependency, framework headroom).

Input : data/phase2_scores.csv, data/phase1_projects.csv
Output: data/phase3_exposure.csv
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

s = pd.read_csv(DATA / "phase2_scores.csv", dtype=str).fillna("")
p = pd.read_csv(DATA / "phase1_projects.csv", dtype=str).fillna("")
df = s.merge(p[["procedure_key", "keywords", "cpv_all", "gist", "contract_start", "contract_end",
                "nuts_granularity", "location_source", "notice_ids"]], on="procedure_key", how="left")
procs = pd.read_csv(DATA / "procedures_all.csv", dtype=str).set_index("procedure_key")["notice_types"]
df["notice_types"] = df["procedure_key"].map(procs).fillna("")
text = (df["title"] + " " + df["gist"] + " " + df["scope_summary_ai"] + " " + df["keywords"]).str.lower()

# ---- A. grid materiality -------------------------------------------------------------
GRID_OPERATORS = r"tennet|stedin|alliander|enexis|liander"
HIGH = (r"charging|laadinfra|laadpa|oplaad|reefer|batter|accu\b|traction power|tractie|rectifier|gelijkrichter|"
        r"substation|verdeelstation|solar|zonne|\bpv\b|feed-in|heat pump|warmtepomp|e-boiler|electrific|"
        r"all-electric|geotherm|medium-voltage network|middenspanningsnet|e-aansluiting|electricity connection")
MODERATE = (r"treatment plant|rwzi|wwtp|zuivering|pumping station|gemaal|drinkwater|drinking water|membrane|"
            r"district heating|warmtenet|heat network|heat-cold|warmte.?koude|bronnet|metro yard|emplacement|"
            r"pier new build|truck parking|new build")
LIKE_FOR_LIKE = r"replac|renovat|vervang|life-extension|lighting|maintenance"
def grid(i):
    t, auth = text[i], df.at[i, "authority"].lower()
    if df.at[i, "is_advisory_service"] == "True":
        return ("n/a (advisory service)", "procures advice, not physical delivery")
    if re.search(GRID_OPERATORS, auth):
        return ("grid builder",
                "the project is itself network expansion; exposure is contractor capacity and outage windows, not congestion")
    if re.search(HIGH, t):
        return ("high", "scope adds electrical load or feed-in that needs new or increased connection capacity")
    if re.search(MODERATE, t):
        if re.search(LIKE_FOR_LIKE, t) and not re.search(r"new|nieuw", t):
            return ("low", "like-for-like renewal of an existing connected asset")
        return ("moderate", "new process or energy installation with material electrical demand; connection size unknown")
    return ("low", "civil, hydraulic or maintenance scope without material new electrical demand")
g = [grid(i) for i in df.index]
df["grid_materiality"] = [x[0] for x in g]
df["grid_materiality_basis"] = [x[1] for x in g]

def link_feasibility(i):
    gran, src = df.at[i, "nuts_granularity"], df.at[i, "location_source"]
    if df.at[i, "grid_materiality"] in ("low", "n/a (advisory service)"):
        return "not needed"
    if gran == "NUTS3":
        return "not linkable from notice: NUTS3 region spans many supply areas; site postcode needed from tender documents"
    if gran in ("NUTS2", "NUTS1") or "reviewer" in src:
        return "not linkable from notice: province-level location only"
    return "not linkable from notice: national code only"
df["grid_link_feasibility"] = [link_feasibility(i) for i in df.index]

# ---- B. other evidenced exposure signals ------------------------------------------------
def years(i):
    try:
        return (pd.Timestamp(df.at[i, "contract_end"]) - pd.Timestamp(df.at[i, "contract_start"])).days / 365.25
    except Exception:
        return 0
SIGNALS = [
    ("procurement market response", lambda i: "VBE" in df.at[i, "notice_types"].split(";")
        or bool(re.search(r"cancel|withdrawn|re-tender|heraanbesteding|no bids|terminated", text[i]))),
    ("live-operation constraint", lambda i: bool(re.search(
        r"stays open|kept open|limit closures|traffic diversion|while keeping|operating (airport|barrier|plant|yard)|"
        r"live (traffic|operation)|operational (air )?base|in use", text[i]))),
    ("hard external deadline", lambda i: bool(re.search(
        r"subsid|by end 20|deadline|december 20\d\d|by 1 july|2027 deadline|timetable|service frequency", text[i]))),
    ("owner integrates many packages", lambda i: bool(re.search(
        r"wranghe|third-party packages|other contractors|fourth contract|separate realisation|interface", text[i]))),
    ("single-supplier dependency", lambda i: "OZB" in df.at[i, "procedure_code"] if "procedure_code" in df else False),
    ("framework headroom exhausted", lambda i: bool(re.search(r"maximum value|ceiling", text[i]))
        and df.at[i, "procurement_status"].startswith("in delivery")),
]
p2 = pd.read_csv(DATA / "phase1_projects.csv", dtype=str).set_index("procedure_key")["procedure_code"]
df["procedure_code"] = df["procedure_key"].map(p2).fillna("")
for name, test in SIGNALS:
    df[f"exp_{name}"] = [test(i) for i in df.index]
cols = [f"exp_{n}" for n, _ in SIGNALS]
df["exposure_signals"] = df[cols].apply(lambda r: "; ".join(c[4:] for c in cols if r[c]), axis=1)
n = df[cols].sum(axis=1)
grid_flag = df["grid_materiality"].isin(["high"])
df["delivery_exposure"] = [
    "high" if k >= 2 or (k >= 1 and gf) else "medium" if k == 1 or gf else "low / not evidenced"
    for k, gf in zip(n, grid_flag)]

out = df[["procedure_key", "title", "authority", "province", "procurement_status", "grid_materiality",
          "grid_materiality_basis", "grid_link_feasibility", "exposure_signals", "delivery_exposure"]]
out.to_csv(DATA / "phase3_exposure.csv", index=False)
print(out["grid_materiality"].value_counts().to_string())
print(out["delivery_exposure"].value_counts().to_string())
print(out["grid_link_feasibility"].value_counts().to_string())
print(out[out.grid_materiality.isin(["high", "grid builder", "moderate"])][["grid_materiality", "title"]]
      .to_string(max_colwidth=80))
