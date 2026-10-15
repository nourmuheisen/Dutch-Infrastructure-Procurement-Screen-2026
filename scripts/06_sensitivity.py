"""Phase 4: weight-sensitivity test (Kop step 6: portfolio decision under different priorities).

Re-ranks clusters under alternative weightings and reports how often each top-18 cluster
stays in the top 18. Uses the reviewed capability scores; nothing is re-scored.
Output: data/sensitivity.csv
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
m = pd.read_csv(DATA / "master_dataset.csv")
order = pd.read_csv(DATA / "clusters.csv").set_index("cluster_or_project")["cluster_rank"].rename("order")
CAPS = ["investment_planning", "procurement_commercial", "controls_assurance", "asset_lifecycle"]

SCENARIOS = {
    "baseline (equal, timing 0.4, conf 0.3)": ([.25, .25, .25, .25], .4, .3),
    "investment & feasibility emphasis":      ([.40, .20, .20, .20], .4, .3),
    "procurement & commercial emphasis":      ([.20, .40, .20, .20], .4, .3),
    "controls & assurance emphasis":          ([.20, .20, .40, .20], .4, .3),
    "asset & lifecycle emphasis":             ([.20, .20, .20, .40], .4, .3),
    "relevance only (no timing/confidence)":  ([.25, .25, .25, .25], .0, .0),
    "timing-led (timing modifier 0.7)":       ([.25, .25, .25, .25], .7, .3),
}
N = 18
ranks = {}
for name, (w, mt, mc) in SCENARIOS.items():
    rel = sum(m[c] * wi for c, wi in zip(CAPS, w))
    rel100 = ((rel - 1) / 4 * 100).round(1)          # same rounding as 03_score.py
    tf = 1 - mt + mt * (m["timing_score"] - 1) / 4
    cf = 1 - mc + mc * (m["confidence"] - 1) / 4
    pr = (rel100 * tf * cf).round(1)
    t = m.assign(pr=pr, rel=rel100).sort_values(["pr", "rel"], ascending=False)
    g = (t.groupby("cluster_or_project", sort=False).first()[["pr", "rel"]]
          .loc[lambda x: x.index.isin(m.loc[m.confidence >= 2.5, "cluster_or_project"])]
          .join(order).sort_values(["pr", "rel", "order"], ascending=[False, False, True]))
    # exact ties keep the published baseline cluster order (data/clusters.csv)
    ranks[name] = pd.Series(range(1, len(g) + 1), index=g.index)

R = pd.DataFrame(ranks)
base = R.iloc[:, 0]
R["in_top18_count"] = (R.iloc[:, :len(SCENARIOS)] <= N).sum(axis=1)
R["best_rank"] = R.iloc[:, :len(SCENARIOS)].min(axis=1)
R["worst_rank"] = R.iloc[:, :len(SCENARIOS)].max(axis=1)
R = R.sort_values(R.columns[0])
R.to_csv(DATA / "sensitivity.csv")
top = R[R.iloc[:, 0] <= N]
print(top[["in_top18_count", "best_rank", "worst_rank"]].to_string())
print("\nclusters reaching top 18 in >=4 of 7 scenarios but not in baseline top 18:")
print(R[(R.iloc[:, 0] > N) & (R["in_top18_count"] >= 4)][["in_top18_count", "best_rank", "worst_rank"]].to_string())
base_top = set(base[base <= N].index)
overlap = {c: len(set(R[c][R[c] <= N].index) & base_top) for c in SCENARIOS}
print("\noverlap with baseline top 18:", overlap)
