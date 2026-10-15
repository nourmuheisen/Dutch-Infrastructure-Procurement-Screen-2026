# Phase 5 — Methodology and validation report

**Question.** Which Dutch public infrastructure procurement notices published in 2026 describe problems where Capital Projects & Infrastructure advisory capabilities (investment planning, procurement and commercial management, project controls and delivery assurance, asset and lifecycle management) are most relevant, and how far can that be shown from public evidence?

**Answer in brief.** From 267 TenderNed notices (183 procedures, 154 projects or programmes), 18 clusters are shortlisted. Eight of them stay in the top 18 under all seven weighting scenarios. Every field checked against the official notice PDFs matched. The main weaknesses are a non-random sample that leans towards May–October, paraphrased descriptions, missing contract values, and no usable grid-capacity link.

---

## 1. Data collection

| Step | What was done | Output |
|---|---|---|
| Source choice | TED and TenderNed both attempted. TED API and pages were unreachable (network allowlist; robots policy). TenderNed's public API worked through the web-fetch tool and republishes all Dutch European notices (154 of 183 procedures carry a TED number). | `reports/phase1_collection_log.md` |
| Stratified queries | One listing query per CPV code across five strata (energy, transport, water, renewal, advisory), publication 1 Jan – 14 Oct 2026. | `raw/listings_*.tsv` (456 rows) |
| Detail records | Latest notice of each in-scope procedure fetched from the detail endpoint. | `raw/details_*.jsonl` (183) |
| Official PDFs | Fetched for 26 notices (18 shortlist leads + 8 random) for validation, values and winners. | `data/validation_pdf_extracts.csv` |
| Context sources | Rijkswaterstaat news (SROK PPB 2; Van Brienenoordbrug contracts), authority pages. | cited per shortlist entry |

## 2. Cleaning and de-duplication

1. **Notice de-duplication.** 456 listing rows → 411 unique notices (45 returned by several CPV queries).
2. **Procedure grouping.** Notices for the same procurement (prior information, contract notice, rectification, award, modification) are grouped by the Rijkswaterstaat 8-digit project number where present, else by normalised authority + title. Four multi-title procedures were grouped by hand and listed in the script (Stedin HV routes, RET welding, Den Haag INTHR, Enschede Pathmos). 411 notices → 287 procedures.
3. **Infrastructure screen.** Keyword and authority rules exclude buildings and non-infrastructure services; each decision and the term that triggered it is logged (`data/screening_log.csv`). 287 → **183 procedures (267 notices)**.
4. **Status.** Derived from the latest non-rectification notice type, with explicit rules for market consultations and qualification systems.
5. **Location.** NUTS code from the notice (88), otherwise authority seat (61) or place name in the title (13), each labelled with its source; 21 national/unknown.
6. **Programme clusters.** 13 hand-defined clusters group procedures that are slices of one client problem (e.g. five Oosterscheldekering contracts). 183 procedures → 154 projects/clusters. A cluster takes the priority of its highest-ranked member.

## 3. Scoring logic

Full rubrics, signals and weights are in `reports/phase2_scoring_model.md`; the configuration is in `scripts/scoring_config.json`.

- **Four capability scores (1–5)**, each with a rubric that names the evidence required for each level. Contract size is not a criterion.
- **Relevance (0–100)** = weighted mean of the four, rescaled. Default weights are equal (0.25) and adjustable.
- **Timing (1–5)** from procurement status: pre-tender 5, terminated (re-procurement likely) 4, tendering/award pending/qualification 3, awarded/in delivery 2.
- **Evidence confidence (1–5)** from description substance, location precision, CPV richness, keywords and number of 2026 notices.
- **Priority** = relevance × timing factor × confidence factor, with modifier strengths 0.4 (timing) and 0.3 (confidence). Multiplicative, so thin evidence cannot be offset by a high score elsewhere.
- **Kept separate from priority:** delivery exposure, grid materiality and advisory position (Phase 3). A project that is hard to deliver is not automatically a better opportunity.

## 4. AI-assisted classification

AI was used in three places, each with a human-readable record:

| Use | Control |
|---|---|
| Extracting and paraphrasing notice content (web-fetch model) | Identifiers, dates and codes requested literally; paraphrases labelled `scope_summary_ai`; checked against PDFs (section 5). |
| Rule-based signal scoring | Deterministic regex signals per capability, with sentences that negate a scope ("PM not included") removed first. Matched evidence stored per score. |
| Reviewed adjustments | Every one of the 183 records was read and the rule score adjusted where the rubric warranted it; 187 adjustments, each with a one-line rationale in `data/review_adjustments.csv`. Both the rule score and the reviewed score are kept in the master dataset. |

**Rule versus review.** 74.5% of capability scores were unchanged by review. Review mostly raised scores (raised/lowered: investment 31/2, procurement 52/0, controls 58/1, asset 42/1; mean absolute change 0.20–0.51 points, largest for controls). The rules are conservative on terse notices: a description that lists "multi-discipline renewal of a bridge in use" without the words *planning* or *interfaces* gets a low rule score for controls. This is the main place where judgement enters the model, so the website should show both scores.

## 5. Validation against original sources

### 5.1 Field-level check of 26 notices against the official PDF

Sample: the 18 shortlist lead notices plus 8 drawn at random from the rest (`random_state=42`). Script: `scripts/07_validate.py`; results: `data/validation_results.csv`.

| Field | Result |
|---|---|
| Title (similarity ≥ 0.9) | 26/26 |
| Contracting authority | 26/26 |
| Notice type (form family; rectifications checked against the form they correct) | 26/26 |
| Main CPV code | 26/26 |
| NUTS location | 14 match, 0 mismatch; 11 not testable (pipeline has national code only); 1 PDF gives a place name only |
| Publication date | 16 same day, 7 one day apart, 2 two days apart, 1 missing in PDF. The offsets are PDF dispatch date versus TenderNed publication date, not errors. |

### 5.2 Content discrepancies found

| Notice | Finding | Treatment |
|---|---|---|
| Stedin HS-tracé (436451) | PDF states **three lots**; the pipeline summary from earlier notices said two. | PDF treated as authoritative; flagged in the shortlist. |
| A9 Gaasperdammerweg (443330) | Title/number mismatch flagged in Phase 1. PDF shows the notice covers A9 and, as lot 1, a late publication of 2nd Coentunnel changes. | Flag resolved; record kept. |
| Almelo Henriëtte Roland Holstlaan (426571) | Deadline field shows 2024 in a 2026 notice. | Source-data error noted; not used for timing. |
| De Brand (443701) | Duration field malformed in the PDF. | Start date used; duration left blank. |
| Van Brienenoordbrug arches (443994) | PDF names Mammoet Europe B.V.; RWS news (9 Oct 2026) names consortium SAMEN (Mammoet + Sarens). | Both recorded. |
| Rail siding (429569) | Extraction model rendered *raccordement* as a power connection (Phase 1). | Corrected by hand before scoring. |

### 5.3 Values and winners

14 of 26 PDFs carry a usable value; 6 carry placeholders (€0, €1 or €2) and are treated as not stated. Recovered values include Stedin HS-tracé (est. €385m), Drechttunnel (€233m, Combinatie DSH), Krammer locks (€357.3m, Besix), A16 Rotterdam (€655.6m, De Groene Boog), Van Brienenoord arches (€149.05m), Merwehaven heat concession (€204.4m) and TenneT EU-302 (€800m raised to €1.4bn). Values are reported for context only and do not enter the scores.

### 5.4 Robustness of the ranking

Seven weighting scenarios (`scripts/06_sensitivity.py`). Eight clusters are in the top 18 in all seven; four more in six of seven. Overlap of each scenario's top 18 with the baseline ranges from 12 (asset-lifecycle emphasis) to 17 (procurement or controls emphasis). Scenario scores use the same rounding as the baseline, and exact ties keep the published cluster order: rank 18 is a three-way tie at 33.7 (Van Brienenoordbrug, Spijkenisserbrug, Arenatunnel). Detail in `reports/phase4_shortlist.md`.

### 5.5 Advisory-contract check

For each shortlisted project, the 2026 sample was searched for linked advisory awards, and targeted web searches were run for the top entries. No project-specific advisory award was found for any of the 18. For the six Rijkswaterstaat entries, project-control and contract-management advice is bought through the SROK PPB 2 framework (awarded 1 Jul 2025; PwC Advisory named in lots 1 and 2).

## 6. Limitations

1. **Sample, not census.** Newest-first ordering per CPV query concentrates the sample in May–October 2026. Findings describe the sample.
2. **Paraphrased text.** Descriptions are model paraphrases. Scores rest on them; the PDF check confirms identifiers and codes, not every scope detail.
3. **Inferred need.** The model infers where advice *fits*; it does not observe demand for advice. No shortlist entry is a confirmed advisory requirement except where stated.
4. **Missing values.** Only 4 of 183 descriptions state a value; size could not have been used even if wanted.
5. **Grid data not linked.** The Netbeheer capacity map could not be retrieved, and notices are too coarsely located to join to it. No grid figures appear anywhere.
6. **Single reviewer.** One reviewer applied the rubric; no second-rater agreement was measured.
7. **Clusters are judgement.** Programme clusters were defined by hand; different groupings would shift some ranks.
8. **Private owners under-represented.** Schiphol, NetVerder, Stedin and similar publish only what procurement law requires.

## 7. Improvements for the next iteration

| Improvement | Effect |
|---|---|
| Use the TenderNed bulk archive (Excel/JSON through Q3 2026) | Full 2026 census instead of a stratified sample; verbatim descriptions; values and winners for all awards. |
| Allow the Netbeheer capacity-map domain; take site postcodes from tender documents for the ~45 grid-material projects | Makes the grid-exposure test in Phase 3 runnable. |
| Second rater on a 30-record subsample | Measures rubric reliability (e.g. weighted kappa). |
| Track modification notices over time | Turns contract changes into a delivery-pressure indicator per authority. |
| Add RWS meerjarenoverzicht vernieuwingsopgave 2026–2030 | Places the RWS entries in the forward pipeline. |
| Read authority board papers for the top entries | Confirms budgets, decision dates and whether advisers are engaged. |

## 8. Reproducing the analysis

```
python scripts/01_consolidate.py      # notices -> procedures, screen
python scripts/02_merge_details.py    # detail records, location, status
python scripts/03_score.py            # capability scores, confidence, timing, priority
python scripts/04_exposure.py         # grid materiality, delivery exposure
python scripts/05_shortlist.py        # master dataset, clusters
python scripts/06_sensitivity.py      # weighting scenarios
python scripts/07_validate.py         # PDF validation, rule/review agreement
python scripts/08_shortlist.py        # annotated shortlist
python scripts/09_phase4_report.py    # shortlist report
python scripts/10_export_site.py      # website data bundle and map geometry
python scripts/11_build_site.py       # website build
```

Weights and modifiers are changed in `scripts/scoring_config.json`; rerun from step 3.
