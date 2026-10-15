# Phase 1 — Collection log

Run date: 15 October 2026. Publication window: 1 January – 14 October 2026.

## Sources attempted

| Source | Route | Result |
|---|---|---|
| TED Search API (`api.ted.europa.eu/v3`) | Python from the cloud workspace | Refused by the workspace network allowlist (proxy 403). |
| TED Search API | Web-fetch tool, GET | Fails (the search endpoint expects POST). |
| TED notice pages (`ted.europa.eu`) | Web-fetch tool | Blocked by the site's robots policy. |
| TenderNed public API (`/papi/tenderned-rs-tns/v2/publicaties`) | Python | Refused by the allowlist. |
| TenderNed public API | Web-fetch tool | **Works.** Used for all collection. |
| TenderNed notice PDFs (`/publicaties/{id}/pdf`) | Web-fetch tool | Works; exposes winner and awarded value. Used in Phase 5 validation. |
| TenderNed bulk archives (Excel/JSON, through Q3 2026) | Python | Not reachable from this workspace. Recommended for the next iteration. |

TenderNed republishes every Dutch above-threshold (European) notice that also goes to TED: 154 of the 183 procedures carry a TED publication number, so TED coverage is retained through TenderNed.

## Method

1. **Stratified listing queries.** One TenderNed listing query per CPV code (the API's `cpvCodes` filter matches the exact code anywhere in a notice's CPV list; it is not hierarchical, and only the first `cpvCodes` value is honoured). Date filter `publicatieDatumVanaf=2026-01-01`, `publicatieDatumTot=2026-10-14`. Pages of 25, newest first. For high-volume codes (bridges/tunnels 161 notices, water engineering 288 in H1 alone, roads 66) additional pages or date windows were fetched to reach back to January.

   | Stratum | CPV codes queried |
   |---|---|
   | Energy | 45231400-9 HV lines, 45251000-2 power plant/heating, 45232140-2 district heating, 45232200-4 HV ancillary, 09332000-5 solar |
   | Transport | 45233120-6 roads, 45234100-7 rail, 45221000-2 bridges & tunnels (pages 1, 4, 6), 45241000-1 ports |
   | Water | 45240000-1 water engineering (two windows), 45246000-3 flood control, 45246400-7 flood prevention, 45252000-3 treatment plants |
   | Renewal | 45453000-7 overhaul & refurbishment |
   | Advisory | 71541000-2 construction PM, 71241000-9 feasibility/advice, 71311000-1 civil engineering advice, 71242000-6 project preparation & cost estimation, 79421000-1 project management, 79411000-8 management consultancy |

2. **Extraction.** The web-fetch tool passes each API response through a small language model. It was instructed to return identifiers, dates, codes, names and titles literally and to paraphrase descriptions in English (it declines to reproduce long source text verbatim). Outputs were transcribed into `raw/listings_*.tsv`.

3. **Consolidation** (`scripts/01_consolidate.py`). 456 raw rows → **411 unique notices** (45 notices returned by more than one CPV query). Notices were grouped into **287 procedures** using the Rijkswaterstaat 8-digit project number where present, otherwise normalised authority + title. Four procedures whose titles vary between notices were grouped manually (listed in the script).

4. **Infrastructure screen.** A documented keyword and authority rule excluded 104 procedures whose object is a social/real-estate building or a non-infrastructure service (schools, hospitals, offices, swimming pools, housing programmes, nitrogen reporting, ICT advice, terminal buildings, local street redesigns). Every decision and the matched term is in `data/screening_log.csv`. The rules were refined once after manual review of the first pass. **183 procedures (267 notices) remain in scope.**

5. **Detail records** (`raw/details_*.jsonl`, `scripts/02_merge_details.py`). The latest notice of each in-scope procedure was fetched from the detail endpoint: CPV codes, NUTS codes, TED number, contract start/end, award and termination flags, keywords, and a paraphrased scope summary. All 183 IDs resolved; the notice type in the listing matched the detail record in 183/183 cases.

## Resulting dataset — `data/phase1_projects.csv`

| | Procedures |
|---|---|
| In scope | 183 |
| By stratum | transport 67, water 54, energy 29, advisory 22, multi-stratum 10, renewal 1 |
| Awarded | 61 |
| Tender closed, award pending | 39 |
| Pre-tender (market consultation / prior information) | 33 |
| In delivery (contract modification) | 22 |
| Open for tender on 15 Oct 2026 | 19 |
| Terminated early | 7 |
| Qualification system open (continuous) | 2 |

*Status counts updated after the Phase 2 status-rule fix (rectifications no longer inherit status; qualification systems and titled market consultations classified explicitly).*

## Missing data

| Field | Coverage | Note |
|---|---|---|
| Contract value | **4 / 183** stated in the description | The detail JSON has no value field. Award PDFs carry the awarded value; retrieved for the shortlist only (Phase 5). |
| Location | 88 from notice NUTS code; 61 from authority seat; 13 from place names in the notice; **21 national or unknown** | 88 notices carry only the national code `NL`. Reviewer-coded locations are labelled as such. |
| Winner / contractor | Not in the detail JSON | Available in award PDFs; retrieved for the shortlist. |
| Description | Present for most; ~10 notices only point to the tender guide | Scope summaries are AI paraphrases, not source text. |

## Limitations

- **Not a random sample.** Newest-first ordering within each CPV query concentrates the sample in May–October 2026; January–April is under-represented. Results describe this sample, not the 2026 market.
- **CPV noise.** Exact-match CPV filtering returns school renovations under power-plant codes and similar; the screen removes these, but some borderline procedures remain.
- **Advisory strata pre-screened at transcription.** For the two 79xxx management-consultancy codes, clearly unrelated rows (reintegration services, broadcasting, health programmes) were not transcribed. The other strata were transcribed in full.
- **AI-mediated extraction.** One model error was caught and corrected by hand (it rendered *raccordement*, a rail siding, as a power connection; marked in the record). One listing ID was mis-typed by the model and self-corrected. Identifier accuracy is checked in Phase 5 against the official PDF.
- **Contract modifications included.** 22 procedures appear only through 2026 modification notices for contracts awarded years earlier (e.g. A16 Rotterdam 2017, A27/A1 2015). They show live delivery programmes, not new procurement.
