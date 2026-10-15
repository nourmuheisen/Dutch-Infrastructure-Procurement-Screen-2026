# Phase 2 — CP&I relevance model

## Design principles

1. **Four separate axes, never blended into one number by default.** *CP&I relevance* (what kind of advisory problem the project poses), *delivery exposure* (Phase 3), *evidence confidence* (how much the public record actually tells us) and *timing / commercial position* (whether a window is open, and whether someone already holds it).
2. **Size is not a criterion.** Contract value is disclosed for 4 of 183 procedures, and a large, simple dredging framework poses a smaller advisory problem than a modest bridge renewal under live traffic. No rubric level depends on value.
3. **Every point is traceable.** Rule scores record which named signal fired. Reviewer adjustments are stored separately with a written rationale, so the two can be compared.
4. **Mirrors Fons Kop's six-step prioritisation logic** (PwC, May 2026):

   | Kop step | Where it sits in this model |
   |---|---|
   | 1. Classification | Phase 1 strata, CPV, asset type, procurement stage |
   | 2. Mandatory criteria | Infrastructure screen (in scope / out of scope, logged) |
   | 3. Resource constraints | Delivery exposure axis: grid capacity, market capacity signals (failed tenders, re-tenders) |
   | 4. Societal value | Asset criticality signal (flood defences, national networks, single points of failure) inside the asset and controls rubrics |
   | 5. Deliverability | Controls & delivery assurance rubric; evidence confidence |
   | 6. Portfolio decision | Weighted ranking with adjustable weights and a sensitivity test |

## Capability rubrics (1–5)

A score is the level whose evidence requirement is met by the notice record. Where evidence is absent the score stays low; absence of evidence is not evidence of absence, and is reflected in the confidence axis rather than inflated here.

### 1. Investment planning & feasibility
*Is there an open question about whether, what, when or how much to invest?*

| Score | Evidence requirement |
|---|---|
| 1 | Investment decided, execution-only scope, no optionality visible. |
| 2 | Decided, but with options, extensions or a life-extension decision implied. |
| 3 | An open investment question is visible: uncommitted later phase, funding/subsidy condition, replace-versus-renovate, early market consultation on scope. |
| 4 | Pre-design stage: consultation before any design, feasibility or concept work procured, multi-project programme to prioritise. |
| 5 | A strategic, multi-option investment decision of regional or national significance (network concept selection, scaling a sector) with the options still open. |

### 2. Procurement & commercial management
*How demanding is the procurement and contracting problem?*

| Score | Evidence requirement |
|---|---|
| 1 | Standard single works or supply contract, open procedure, no complexity signals. |
| 2 | Standard framework or call-off; minor variation. |
| 3 | Non-standard form: bouwteam/two-phase, competitive dialogue, D&C (UAV-GC), multi-lot strategy, or contract modification. |
| 4 | Strategy actively being designed (consultation on contracting or collaboration models), or procurement difficulty evidenced (termination, re-tender, no bids), or material ceiling changes. |
| 5 | Several strong signals at programme scale: e.g. multi-year multi-lot framework strategy for a network operator, DBFM/concession with financing, or contractor-market strategy for a scaling sector. |

### 3. Project controls & delivery assurance
*How hard is it to deliver on time, on budget and safely?*

| Score | Evidence requirement |
|---|---|
| 1 | Single discipline, single site, short, low interface. |
| 2 | Some complexity: multi-site framework, or one to two years. |
| 3 | Multi-discipline or multi-year with operational constraints. |
| 4 | Multi-discipline **and** live-operation or interface management **and** multi-year; or scope change on a running major contract. |
| 5 | Programme level: several interdependent contracts or contractors, controls explicitly procured, or a nationally critical asset. |

### 4. Asset & lifecycle management
*Is the project about the long-term condition and performance of existing assets?*

| Score | Evidence requirement |
|---|---|
| 1 | New-build with no lifecycle component. |
| 2 | Routine maintenance (dredging, mowing) without asset-management decisions. |
| 3 | Renovation or major maintenance of an asset, or a maintenance phase in the contract. |
| 4 | Life-extension or renewal decision on a critical asset, or performance-based maintenance with condition data. |
| 5 | Portfolio-level asset management: several assets, inspection-driven plans, asset information on critical infrastructure. |

## Rule-based signals (baseline)

Implemented in `scripts/03_score.py`. Each capability starts at 1; each fired signal adds its weight; the total is capped at 5. Text matching runs on the title, listing gist, keywords, stated duration/value and the scope summary **with negative sentences removed** (the extraction model frequently writes "project management services are not mentioned"; without this step those sentences would fire the very signals they deny).

| Capability | Signals (weight) |
|---|---|
| Investment planning | early market engagement (1.0); feasibility, concept or business-case work (1.5); feasibility CPV 71241000 (1.0); later phase not committed (1.0); funding/subsidy condition (0.5); end-of-life decision (0.5); programme/portfolio (0.5); strategic energy-transition investment (0.5) |
| Procurement & commercial | competitive dialogue (1.0); negotiated procedure (0.5); bouwteam/two-phase (1.0); integrated contract form (1.0); framework/lots/qualification (0.5); contracting strategy under design (1.5); procurement difficulty (1.0); ceiling change (0.5); independent price/cost review (0.5) |
| Controls & assurance | ≥3 disciplines (1.5) or 2 disciplines (0.5); live operation (1.0); interfaces (1.0); multi-contract/multi-site (0.5); ≥4-year horizon (0.5); hard external deadline (0.5); scope change on running major contract (0.5); controls explicitly in scope (1.5) |
| Asset & lifecycle | renovation/replacement (1.0); life-extension (1.5); maintenance/use phase (1.0); asset information/inspection (1.0); critical asset type (0.5) |

## AI-assisted review

Rules are blind to meaning in terse notices (a two-line TenneT notice raising a framework ceiling by €600 million fires almost nothing). Every procedure is therefore read against the rubric by the AI reviewer, using the full record (title, authority, status, CPV, scope summary). Where the reviewed level differs from the rule score, the change and a one-line rationale are written to `data/review_adjustments.csv` and applied on top of the rule score. The share of scores left unchanged is reported as rule–review agreement in Phase 5.

## Evidence confidence (1–5)

Starts at 1: +1.5 substantive description (not a placeholder or a pointer to the tender guide); +1.0 sub-national NUTS location (+0.5 if reviewer-coded); +0.5 several CPV codes; +0.5 keywords; +0.5 several notices in 2026. Capped at 5.

## Timing and commercial position

| Procurement status | Timing (1–5) | Meaning for an adviser |
|---|---|---|
| Pre-tender (market consultation / prior information) | 5 | Strategy and scope still open |
| Terminated | 4 | Re-procurement likely; strategy needs rework |
| Tendering / award pending / qualification system open | 3 | Works procurement live; client-side advisers usually already engaged |
| Awarded / in delivery | 2 | Controls and assurance during delivery only |

**Advisory position flags** (text, not scored): advisory already awarded in this procedure; advisory procurement in progress; Rijkswaterstaat projects route project- and contract-control advice through the SROK PPB 2 framework, on which PwC has been a party since July 2025 ([Consultancy.nl, 2 July 2025](https://www.consultancy.nl/nieuws/62858/rijkswaterstaat-kiest-partners-voor-projectbeheersing-en-contractbeheersing)).

## Composite

- **Relevance** = Σ weightᵢ × capabilityᵢ, rescaled to 0–100. Default weights 0.25 each (`scripts/scoring_config.json`).
- **Priority** = relevance × timing factor × confidence factor. Each factor ranges from (1 − modifier) to 1.0; defaults are timing 0.4 and confidence 0.3. Multiplicative by design: an open window or a well-documented notice cannot turn an irrelevant project into a priority. (An additive first version did exactly that — a metro weed-control consultation reached the top ten — and was replaced.)
