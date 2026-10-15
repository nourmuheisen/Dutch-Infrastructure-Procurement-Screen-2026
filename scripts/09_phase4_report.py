"""Writes reports/phase4_shortlist.md from data/shortlist.csv and the cluster/sensitivity tables."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "data" / "shortlist.csv").fillna("")
c = pd.read_csv(ROOT / "data" / "clusters.csv").fillna("")
s = pd.read_csv(ROOT / "data" / "sensitivity.csv", index_col=0)

def eur(v):
    if v == "" or v is None: return "not stated"
    v = float(v)
    return f"€{v/1e6:,.1f}m" if v >= 1e6 else f"€{v:,.0f}"

L = []
L.append("""# Phase 4 — Ranked shortlist of CP&I-relevant projects

**Sample:** 183 in-scope procedures (267 TenderNed notices published 1 Jan – 14 Oct 2026), grouped into 154 projects or programme clusters. **Shortlist:** the 18 highest-priority clusters with evidence confidence ≥ 2.5, under equal capability weights.

## How to read this list

- **Priority (0–100)** = capability relevance × timing factor × confidence factor (Phase 2). It ranks *where CP&I-type advice fits the problem the notice describes and whether there is still time to influence it*. It is not a forecast that the authority will buy advice, and contract size plays no part in it.
- **Stable in x/7** = in how many of seven weighting scenarios (one per capability emphasis, relevance-only, timing-led) the cluster stays in the top 18. Use it to tell robust picks from picks that depend on the weights.
- **Advisory status** separates what was found from what was not. "Not found" means not found in the 2026 TenderNed sample and a targeted web search; it does not mean no adviser is engaged.
- **Values** come from the official notice PDFs where the authority filled them in. Placeholders (€0, €1, €2) are reported as not stated.
- Delivery exposure and grid materiality (Phase 3) are shown beside the ranking, not inside it.

## Shortlist at a glance

| # | Project | Authority | Status | Priority | Conf. | Stable | Value (PDF) | Main capabilities |
|---|---|---|---|---|---|---|---|---|""")
for _, r in d.iterrows():
    L.append(f"| {r['rank']} | {r.project} | {r.authority} | {r.status} | {r.priority_0to100:.1f} | {r.confidence_1to5} | {r.scenarios_in_top18_of_7}/7 | {eur(r.value_eur_from_pdf)} | {r.main_capabilities} |")

L.append("""
## What the shortlist says

**1. The open strategy questions sit with regional and network owners, not with Rijkswaterstaat.** Ranks 1–4, 6, 8, 10 and 12 are pre-tender: water boards (Wetterskip Fryslân, Aa en Maas), grid and heat-network companies (Stedin, NetVerder), RET, a municipality and Schiphol are asking the market how to contract, phase and package work. These are the points where investment-planning and procurement advice changes outcomes. The Rijkswaterstaat entries are mostly awarded or in delivery, and RWS buys project-control and contract-management advice through its SROK PPB 2 framework, where PwC is already a party.

**2. Renewing assets that stay in use produces visible change in delivery.** Three shortlisted RWS contracts were modified in 2026: pipe brackets on the Oosterscheldekering replaced after a TNO study, extra work at the Krammer locks for radio-coverage problems possibly linked to a nearby wind farm, and repairs to Terbregseplein structures outside the A16 scope. On the watch-list, TenneT raised its EU-302 framework ceiling from €800m to €1.4bn, citing rapid growth, inflation and scope. Modification notices are a public, repeatable signal of where controls and change management are under pressure.

**3. On grid capacity, the evidence points to the contractor market, not to congestion maps.** Grid capacity matters to 45 of 183 procedures, but none can be located precisely enough to join to the Netbeheer capacity map (Phase 3). What the notices do show is supply-chain strain: Stedin's €385m high-voltage programme, TenneT's framework increases and re-qualification. That makes grid expansion a procurement and commercial question.

## Robustness

Scenario ranks use the same rounding as the baseline score; exact ties keep the published cluster order.

""")
L.append("| Stable in | Clusters |\n|---|---|")
for k in (7, 6, 5, 4, 3):  # counts from data/sensitivity.csv
    names = d[d.scenarios_in_top18_of_7 == k].project.tolist()
    if names: L.append(f"| {k}/7 | {'; '.join(names)} |")
L.append("""
Eight clusters stay in the top 18 under every weighting. Van Brienenoordbrug (3/7), Sneek (4/7) and A16 (4/7) are in the baseline list only narrowly; Van Brienenoordbrug shares rank 18's priority (33.7) exactly with Spijkenisserbrug and the Amsterdam Arenatunnel, and holds the place only by the published tie order. Van Brienenoordbrug is better read as a reference case for controls across a multi-contract renewal than as a lead (see entry 18).

Overlap of each scenario's top 18 with the baseline: investment emphasis 15, procurement 17, controls 17, asset lifecycle 12, relevance only 13, timing-led 14. The asset-lifecycle and relevance-only scenarios move the list most, because they reward large renewals already in delivery over open strategy questions.

## Entries
""")
for _, r in d.iterrows():
    win = f" Winner: {r.winner_from_pdf}." if r.winner_from_pdf else ""
    L.append(f"""### {r['rank']}. {r.project}

*{r.authority} · {r.status} · priority {r.priority_0to100:.1f} (relevance {r.relevance_0to100:.1f}, timing {r.timing_1to5}, confidence {r.confidence_1to5}) · stable in {r.scenarios_in_top18_of_7}/7, rank range {r.rank_range} · {r.n_procedures} procedure(s) · grid: {r.grid_materiality} · delivery exposure: {r.delivery_exposure}*

**Why it matters for CP&I.** {r.why_it_matters}

**Facts from the official notice.** Value: {eur(r.value_eur_from_pdf)}.{win}

**Advisory status.** {r.advisory_status}

**Evidence gaps.** {r.evidence_gaps}

**Follow-up.** {r.follow_up}

**Sources.** {' · '.join(f'<{u.strip()}>' for u in r.sources.split(' ; '))}
""")

L.append("""## Watch-list (ranks 19–30)

| # | Project | Why it is close | Note |
|---|---|---|---|""")
WATCH = {
 "Spijkenisserbrug": "Renewal of technical and 3B systems on two movable bridges in use",
 "Arenatunnel": "Municipal tunnel renovation, awarded",
 "Overijssel": "Province consulting on large maintenance frameworks for structures and waterways",
 "INTHR": "Multi-year tram infrastructure agreement for new Haaglanden trams",
 "Kademuren Leiden": "Life-extension of historic quay walls",
 "Stuwen": "Major maintenance of four Maas weirs",
 "Integration Consultant": "Gasunie is buying an Integration Consultant for hydrogen network Concept Select — a direct advisory procurement, award pending",
 "Hollandsche IJsselkering": "Storm-surge barrier renewal; 11-year control-system award without prior publication",
 "Everdingen": "A27 DBFM in delivery; contract modified five times in 2026",
 "Sloten": "Tilburg maintenance consultation",
 "TenneT": "EU-302 ceiling +€600m, EU-301 +€79.3m, re-qualification under EU-401/402",
 "Eindhoven Air Base": "Runway renovation at a defence airbase",
}
for _, r in c[c.eligible].iloc[18:30].iterrows():
    note = next((v for k, v in WATCH.items() if k.lower() in r.cluster_or_project.lower()), "")
    L.append(f"| {r.cluster_rank} | {r.cluster_or_project[:90]} | {note} | stable {int(s.loc[r.cluster_or_project].in_top18_count)}/7 |")

L.append("""
Gasunie (25) is the one *confirmed* advisory procurement near the top: a direct-bid route rather than a hypothetical need. It ranks below 18 because notices for advisory services score lower on the asset-lifecycle and controls rubrics by design.

## Advisory contracts already awarded in the sample

The 2026 sample contains advisory awards that show which owners already buy this kind of support (none is for a shortlisted project): NRG Pallas programme integration manager; Arnhem energy advisory; Utrecht wind advisory; Pielis; WRL engineering; Amstelveen cables coordinator; Zwijndrecht design & engineering; an ERTMS study; Rivierenland contract preparation; brook-restoration planning. In progress: Gasunie hydrogen Integration Consultant, Haarlem energy advisory, Noord-Holland DAS, HVC engineering.

## Limits of this list

- A notice describes the works the authority is buying; the need for advice is inferred from scope, procedure and stage. No entry here is a confirmed advisory requirement unless stated.
- Values are missing for most entries; only 4 of 183 notice descriptions state one, and 14 of 26 validated PDFs did.
- Private and semi-public owners (Schiphol, NetVerder, Stedin) publish only what procurement law requires.
""")
(ROOT / "reports" / "phase4_shortlist.md").write_text("\n".join(L))
print("written", len("\n".join(L).split()), "words")
