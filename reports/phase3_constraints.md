# Phase 3 — Infrastructure constraint assessment

## Datasets investigated

| Dataset | What it offers | Access from this environment | Used? |
|---|---|---|---|
| **Netbeheer Nederland capaciteitskaart** | Offtake and feed-in congestion status, queue counts, planned expansions and expected dates; per 6-digit postcode, per regional supply area (*voedingsgebied*), per TenneT area, plus a project file. Seven CSV exports are listed on the official info page (`/api/download/congestie_pc6.csv`, `voedingsgebieden.csv`, `tennetgebieden.csv`, `tennetcongestie.csv`, `voedingsgebieden_year_granularity.csv`, `projecten.csv`, `brondata_documentatie.txt`). | Map page loads but renders no data; every CSV export fails through the web-fetch tool; shell access is blocked by the network allowlist. | **No.** No capacity figures appear anywhere in this analysis. |
| Rijkswaterstaat *Meerjarenoverzicht vernieuwingsopgave bruggen, tunnels en sluizen 2026–2030* (published 8 Dec 2025) | Expected contracting flow for renewal work by object type and year; funded vs not yet funded. | Landing page readable; the PDF is blocked by the site's robots policy. | Context only (existence, scope, update cycle). Figures not retrieved. |
| Rijkswaterstaat SROK PPB 2 framework (Jul 2025) | Who holds RWS project-control and contract-management framework positions. | Readable via news coverage. | **Yes** — advisory-position flag. |
| Rijkswaterstaat news on the Van Brienenoordbrug renewal (2 Sep 2026) | Contract sequence and timing for the Van Brienenoordbrug renewal. | Readable. | **Yes** — shortlist context. |

The capacity map's own disclaimers matter for any future use: it is an indicative snapshot without guarantee; a queue of 0 can mean incomplete data; expansion dates are estimates and can slip.

## Can grid data be linked to projects?

**Geographically — not from notice data.** The capacity map's finest units are the 6-digit postcode and the supply area. The notices locate projects as follows:

| Location precision in the notice | Grid-material projects (high, moderate, grid builder) |
|---|---|
| NUTS3 region (e.g. *Groot-Rijnmond*) | 16 |
| Province, or reviewer-coded from authority seat | 18 |
| National code only | 11 |
| Site postcode or coordinates | **0** |

A NUTS3 region spans dozens of supply areas with different statuses, so assigning one status to a project from its NUTS3 code would be guesswork. Site-level location exists in tender documents (drawings, location annexes) and on authority project pages, not in the notice.

**Temporally — feasible once geography is solved.** The map gives a snapshot status and expected expansion dates per area; 52 of 183 procedures carry contract start/end dates. A defensible test would compare the expected grid-expansion date for the site's supply area with the project's commissioning date.

## Grid materiality (`data/phase3_exposure.csv`)

Grid congestion is only relevant where the project itself needs new or increased connection capacity. Each project was classified from its own scope:

| Class | Count | Meaning | Examples |
|---|---|---|---|
| Grid builder | 8 | The project *is* network expansion; its exposure is contractor capacity and outage windows, not congestion | Stedin HV routes; TenneT EU-401/402 qualification systems and EU-301/302 frameworks; Alliander OS IJmuiden–Velsen |
| High | 13 | Adds load or feed-in needing new connection capacity | RET metro traction-power reinforcement; GVB rectifier substations; truck parking with reefer power and EV-ready supply; geothermal Amsterdam-Amstelveen; Future Grid Crailo; solar parks |
| Moderate | 24 | New process or energy installation with material demand; connection size unknown | New WWTPs (Vergulde Hand, Bennekom); Wranghe drinking-water plant; heat networks; Schiphol C-Pier |
| Low | 117 | Civil, hydraulic or like-for-like renewal | Dredging, roads, quay walls, dikes, bridge and tunnel renewals |
| n/a | 21 | Advisory services | — |

**Result:** grid capacity is materially relevant to 45 of 183 procedures. For none of them can the current congestion status be established from public notice data. The model therefore records *materiality* and *link feasibility*, and leaves the *exposure* undetermined rather than assuming it.

## A pattern the notices do show: strain on the grid-expansion supply chain

Without any congestion data, the grid-builder notices themselves evidence delivery pressure on network expansion:

- TenneT raised the ceiling of framework **EU-302** (civil works for cable connections) by **€600 million** on an €800 million base, and **EU-301** (overhead lines) by **€79.3 million** on €200 million (Oct and Jun 2026).
- TenneT replaced qualification system EU-301 with **EU-401** and opened **EU-402** for cable works, requiring previously qualified contractors to re-apply.
- Stedin's HV route programme ramps from about **€30 million to €65 million a year** over eight years in two lots.

These are statements of the operators' own procurement volumes, not congestion measurements. They point to the contractor market and framework headroom — a procurement and commercial question — as the binding constraint on grid expansion.

## Other evidenced delivery-exposure signals

| Signal | Procedures | What it captures |
|---|---|---|
| Procurement market response | 7 | Termination, re-tender or withdrawal visible in 2026 notices (e.g. Tilburg flanking measures terminated twice) |
| Live-operation constraint | 3 | Explicitly stated works in an operating asset (e.g. Drechttunnel stays open) |
| Hard external deadline | 4 | Subsidy deadlines, timetable increases, fixed completion dates |
| Owner integrates many packages | 7 | E.g. Evides procures the Wranghe drinking-water plant as at least five separate packages |
| Single-supplier dependency | 8 | Negotiated awards without prior publication (e.g. 11-year Hollandsche IJssel barrier control system) |
| Framework headroom exhausted | 2 | Ceiling increases on running TenneT frameworks |

These counts are conservative: the signals match only what the paraphrased notice summaries state explicitly. Many renewals in the sample (locks, movable bridges) are in operating assets without the summary saying so; the reviewed controls scores in Phase 2 capture that, the exposure flags do not.

Combined into **delivery exposure**: high 4, medium 36, low or not evidenced 143. "Not evidenced" is not "low risk"; it means the notice does not say.

## Four axes, kept separate

| Axis | Source | Scale |
|---|---|---|
| CP&I relevance | Phase 2 rubric | 0–100 |
| Delivery exposure | This phase | high / medium / low or not evidenced, plus grid materiality |
| Evidence confidence | Phase 2 | 1–5 |
| Timing and commercial position | Procurement status + advisory flags | 1–5 + text flags |

Exposure is **not** folded into the priority score. A project that is hard to deliver is not automatically a better advisory opportunity, and a congested area does not penalise a dredging contract.

## What would make the grid link work

1. Allow the capacity-map domain (or download the CSVs locally) and store the snapshot date with the data.
2. For the ~45 grid-material projects only, take the site postcode or coordinates from the tender documents or the authority's project page.
3. Join postcode → supply area → status, queue and expected expansion date (offtake for loads, feed-in for solar/storage).
4. Flag exposure only when materiality is high or moderate **and** the area is short of capacity with a queue **and** the expected expansion date falls after planned commissioning.
