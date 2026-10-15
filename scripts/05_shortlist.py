"""Phase 4: master dataset, programme clusters and shortlist.

Related procedures are grouped into programme clusters, because CP&I advises at programme
level and several 2026 notices are slices of one client problem (e.g. HVC renewing three
supply-chain schemes at once). A cluster's priority is that of its highest-priority member.

Input : data/phase2_scores.csv, data/phase3_exposure.csv, data/phase1_projects.csv, scripts/scoring_config.json
Output: data/master_dataset.csv, data/clusters.csv, data/shortlist_candidates.csv
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CFG = json.loads((ROOT / "scripts" / "scoring_config.json").read_text())

s = pd.read_csv(DATA / "phase2_scores.csv", dtype=str)
e = pd.read_csv(DATA / "phase3_exposure.csv", dtype=str)
p = pd.read_csv(DATA / "phase1_projects.csv", dtype=str)
m = (s.merge(e[["procedure_key", "grid_materiality", "grid_materiality_basis", "grid_link_feasibility",
                "exposure_signals", "delivery_exposure"]], on="procedure_key")
      .merge(p[["procedure_key", "notice_ids", "ted_publication_number", "contract_start", "contract_end",
                "closing_date", "value_stated_in_description", "reference_number"]], on="procedure_key"))
for c in ["priority_0to100", "relevance_0to100", "confidence", "timing_score"]:
    m[c] = m[c].astype(float)

CLUSTERS = {
    "TenneT grid-expansion supply chain": ["tennet tso b v|"],
    "HVC heat-network supply-chain renewal": ["n v hvc|"],
    "Oosterscheldekering asset programme": ["RWS-31139442", "RWS-31160061", "RWS-31208914", "RWS-31192916", "RWS-31203739"],
    "Hollandsche IJsselkering": ["RWS-31114126", "RWS-31211853"],
    "Evides Wranghe drinking-water plant": ["evides n v|dwz wranghe"],
    "RET Waalhaven metro yard (Metronet)": ["r e t n v|p 25 037", "r e t n v|vooraankondiging fase 1 uitbreiding opstelsporen"],
    "A9 Gaasperdammerweg DBFM": ["RWS-31003668", "RWS-31066756"],
    "Merwedekanaal T10 dredging": ["provincie zuid holland|baggeren vaarweg"],
    "Province of Overijssel structures & waterways maintenance": [
        "provincie overijssel|groot onderhoud kunstwerken", "provincie overijssel|marktconsultatie groot onderhoud kunstwerken",
        "provincie overijssel|groot onderhoud vaarwegen"],
    "Province of Limburg Heuvelland provincial roads": [
        "provincie limburg|bouwteam reconstructie", "provincie limburg|reconstructie n598", "provincie limburg|marktconsultatie n595"],
    "GVB Amsterdam metro operational technology & power": ["gvb infra b v|"],
    "Enschede climate-adaptation programme": ["MANUAL-enschede|", "gemeente enschede|"],
    "Eindhoven Air Base (defence)": ["rijksvastgoedbedrijf|29183", "rijksvastgoedbedrijf|34723"],
}
def cluster_of(key):
    for name, prefixes in CLUSTERS.items():
        if any(key.startswith(px) for px in prefixes):
            return name
    return None
m["programme_cluster"] = m["procedure_key"].map(cluster_of)
m["cluster_or_project"] = m["programme_cluster"].fillna(m["title"])

m.to_csv(DATA / "master_dataset.csv", index=False)

agg = (m.sort_values("priority_0to100", ascending=False)
        .groupby("cluster_or_project")
        .agg(lead_procedure=("procedure_key", "first"), lead_title=("title", "first"),
             authority=("authority", "first"), n_procedures=("procedure_key", "size"),
             priority=("priority_0to100", "max"), relevance=("relevance_0to100", "max"),
             confidence=("confidence", "max"), timing=("timing_score", "max"),
             statuses=("procurement_status", lambda x: "; ".join(sorted(set(x)))),
             grid=("grid_materiality", lambda x: "; ".join(sorted(set(x)))),
             exposure=("delivery_exposure", "first"),
             advisory_position=("advisory_position", lambda x: " | ".join(sorted({v for v in x if isinstance(v, str) and v}))),
             members=("title", lambda x: " || ".join(x)))
        .sort_values("priority", ascending=False).reset_index())
agg["eligible"] = agg["confidence"] >= CFG["shortlist"]["min_confidence"]
agg["cluster_rank"] = range(1, len(agg) + 1)
agg.to_csv(DATA / "clusters.csv", index=False)
cand = agg[agg["eligible"]].head(30)
cand.to_csv(DATA / "shortlist_candidates.csv", index=False)
print(f"{len(m)} procedures in {len(agg)} clusters/projects; {m['programme_cluster'].notna().sum()} procedures clustered")
print(cand[["cluster_rank", "priority", "relevance", "confidence", "timing", "n_procedures", "cluster_or_project"]]
      .to_string(max_colwidth=70))
