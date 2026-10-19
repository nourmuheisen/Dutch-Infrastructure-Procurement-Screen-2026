"""Website: export the analysis to one JSON bundle (site/data.json) and the map geometry.

Geometry: CBS COROP regions 2025 and provinces 2025 (PDOK, via github.com/cartomap/nl,
gh-pages branch). COROP regions carry the same names as the NUTS 2024 level-3 regions
(eurostat/Nuts2json), which supply the NUTS ids. Projected to SVG units here so the page
needs no map library.
"""
import json, math, re
from pathlib import Path
import pandas as pd
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
DATA, SITE = ROOT / "data", ROOT / "site"
GEO = ROOT / "raw" / "geo"
SITE.mkdir(exist_ok=True)

m = pd.read_csv(DATA / "master_dataset.csv", dtype=str).fillna("")
p = pd.read_csv(DATA / "phase1_projects.csv", dtype=str).fillna("").set_index("procedure_key")
n = pd.read_csv(DATA / "notices_all.csv", dtype=str).fillna("").set_index("publicatieId")
sl = pd.read_csv(DATA / "shortlist.csv", dtype=str).fillna("")
val = pd.read_csv(DATA / "validation_results.csv", dtype=str).fillna("")
vx = pd.read_csv(DATA / "validation_pdf_extracts.csv", dtype=str).fillna("")
cfg = json.loads((ROOT / "scripts" / "scoring_config.json").read_text())
vsum = json.loads((DATA / "validation_summary.json").read_text())

# ---- owner type ---------------------------------------------------------------------
OWNER_RULES = [
    ("Rijkswaterstaat", r"^rijkswaterstaat"),
    ("Water authorities & water companies", r"waterschap|hoogheemraadschap|wetterskip|waternet|evides|waterbedrijf"),
    ("Grid & energy companies", r"stedin|tennet|alliander|gasunie|netverder|\bhvc\b|vattenfall|warmtestad|utilityconnect"),
    ("Transport & port operators", r"r\.e\.t\.|gvb|prorail|schiphol|havenbedrijf|seaports"),
    ("Provinces", r"^provincie"),
    ("Municipalities", r"^gemeente"),
]
def owner_type(a):
    a = a.lower()
    for name, rx in OWNER_RULES:
        if re.search(rx, a):
            return name
    return "Other public bodies"

NUTS2_PROV = {"NL11": "Groningen", "NL12": "Friesland", "NL13": "Drenthe", "NL21": "Overijssel",
              "NL22": "Gelderland", "NL23": "Flevoland", "NL32": "Noord-Holland", "NL35": "Utrecht",
              "NL36": "Zuid-Holland", "NL34": "Zeeland", "NL41": "Noord-Brabant", "NL42": "Limburg"}

def f(x):
    try: return float(x)
    except ValueError: return None

procs = []
for _, r in m.iterrows():
    q = p.loc[r.procedure_key]
    codes = [c for c in r.nuts_codes.split(";") if c]
    regions = sorted({c for c in codes if len(c) == 5})
    provinces = [x for x in r.province.split(";") if x]
    if regions and len(regions) > 2:      # a notice listing many NUTS 3 areas is located to province level
        provinces = sorted({NUTS2_PROV[c[:4]] for c in regions} | set(provinces))
        regions = []
    if regions:
        precision = "region"
    elif provinces:
        precision = "province"
    else:
        precision = "national"
    notices = []
    for nid in r.notice_ids.split(";"):
        if nid in n.index:
            x = n.loc[nid]
            notices.append({"id": nid, "date": x.publicatieDatum, "type": x.typePublicatie, "gist": x.gist})
    notices.sort(key=lambda d: d["date"])
    procs.append({
        "key": r.procedure_key, "title": r.title, "authority": r.authority,
        "owner": owner_type(r.authority), "strata": r.strata, "status": r.procurement_status,
        "cluster": r.cluster_or_project, "programme": r.programme_cluster,
        "s": [f(r.investment_planning), f(r.procurement_commercial), f(r.controls_assurance), f(r.asset_lifecycle)],
        "rule": [f(r.investment_planning_rule), f(r.procurement_commercial_rule), f(r.controls_assurance_rule), f(r.asset_lifecycle_rule)],
        "ev": [r.investment_planning_evidence, r.procurement_commercial_evidence, r.controls_assurance_evidence, r.asset_lifecycle_evidence],
        "review": r.review_note, "timing": f(r.timing_score), "timingNote": r.timing_note,
        "conf": f(r.confidence), "confBasis": r.confidence_basis,
        "priority": f(r.priority_0to100), "relevance": f(r.relevance_0to100),
        "advisory": r.advisory_position, "isAdvisory": r.is_advisory_service == "True",
        "scope": r.scope_summary_ai, "cpv": r.cpv_main, "nuts": codes, "regions": regions,
        "provinces": provinces, "precision": precision, "locSource": q.location_source,
        "grid": r.grid_materiality, "gridBasis": r.grid_materiality_basis,
        "signals": [s for s in r.exposure_signals.split(";") if s.strip()], "exposure": r.delivery_exposure,
        "start": r.contract_start, "end": r.contract_end, "closing": r.closing_date,
        "procedureCode": q.procedure_code, "ted": r.ted_publication_number, "url": r.source_url,
        "notices": notices,
    })

short = []
for _, r in sl.iterrows():
    short.append({k: r[k] for k in ["rank", "project", "lead_procedure", "value_eur_from_pdf", "winner_from_pdf",
                                     "main_capabilities", "why_it_matters", "advisory_status", "evidence_gaps",
                                     "follow_up", "sources", "scenarios_in_top18_of_7", "rank_range"]})

validation = []
vx = vx.set_index("notice_id")
for _, r in val.iterrows():
    x = vx.loc[r.notice_id]
    validation.append({"id": r.notice_id, "sample": x.loc["sample"], "title": r.title,
                       "titleSim": f(r.title_similarity), "titleOk": r.title_ok == "True",
                       "authOk": r.authority_ok == "True", "typeOk": r.notice_type_ok == "True",
                       "cpvOk": r.cpv_main_ok == "True", "nuts": r.nuts_check,
                       "dateDiff": f(r.pub_date_diff_days), "value": f(r.pdf_value_eur),
                       "placeholder": r.value_placeholder_in_pdf == "True",
                       "winner": r.pdf_winners, "note": r.pdf_note, "pdfType": x.pdf_notice_type})

# ---- geometry -----------------------------------------------------------------------
LON0, LAT0, K = 3.30, 53.60, 250.0
COS = math.cos(math.radians(52.2))
def proj(lon, lat): return ((lon - LON0) * COS * K, (LAT0 - lat) * K)
def path_of(geom):
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    out = []
    for poly in polys:
        for ring in [poly.exterior] + list(poly.interiors):
            pts = [proj(x, y) for x, y in ring.coords]
            out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
    return "".join(out)

nuts = json.loads((GEO / "nuts3_10M.json").read_text())
name2id = {ft["properties"]["na"].replace("’", "'"): ft["properties"]["id"]
           for ft in nuts["features"] if ft["properties"]["id"].startswith("NL")}
corop = json.loads((GEO / "coropgebied_2025.geojson").read_text())
prov = json.loads((GEO / "provincie_2025.geojson").read_text())
regions = []
for ft in corop["features"]:
    nm = ft["properties"]["statnaam"]
    g = shape(ft["geometry"]).simplify(0.0015, preserve_topology=True)
    rid = name2id[nm]
    c = g.representative_point()
    cx, cy = proj(c.x, c.y)
    regions.append({"id": rid, "name": nm, "province": NUTS2_PROV[rid[:4]], "d": path_of(g),
                    "cx": round(cx, 1), "cy": round(cy, 1)})
provinces = []
for ft in prov["features"]:
    nm = ft["properties"]["statnaam"].replace("Fryslân", "Friesland")
    g = shape(ft["geometry"]).simplify(0.0015, preserve_topology=True)
    c = g.representative_point(); cx, cy = proj(c.x, c.y)
    b = g.bounds; x0, y1 = proj(b[0], b[1]); x1, y0 = proj(b[2], b[3])
    provinces.append({"name": nm, "d": path_of(g), "cx": round(cx, 1), "cy": round(cy, 1),
                      "bbox": [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)]})
allg = unary_union([shape(ft["geometry"]) for ft in prov["features"]]).bounds
x0, y1 = proj(allg[0], allg[1]); x1, y0 = proj(allg[2], allg[3])

corder = pd.read_csv(DATA / "clusters.csv", dtype=str).fillna("")
cluster_order = {r.cluster_or_project: int(r.cluster_rank) for _, r in corder.iterrows()}
for x in procs:
    x["order"] = cluster_order[x["cluster"]]

bundle = {
    "meta": {"snapshot": "2026-10-14", "built": "2026-10-15", "nNotices": sum(len(x["notices"]) for x in procs),
             "funnel": [["Listing rows", 456], ["Unique notices", 411], ["Procedures", 287],
                        ["In scope", 183], ["Projects / clusters", m.cluster_or_project.nunique()], ["Shortlist", 18]],
             "weights": cfg["capability_weights"], "modifiers": cfg["priority_modifiers"],
             "minConf": cfg["shortlist"]["min_confidence"], "N": cfg["shortlist"]["size"],
             "validationSummary": vsum},
    "procs": procs, "shortlist": short, "validation": validation,
    "geo": {"regions": regions, "provinces": provinces,
            "bbox": [round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)]},
}
(SITE / "data.json").write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")))
print("procs", len(procs), "notices", bundle["meta"]["nNotices"], "regions", len(regions),
      "size KB", round((SITE / "data.json").stat().st_size / 1024))
print(pd.Series([x["owner"] for x in procs]).value_counts().to_string())
print(pd.Series([x["precision"] for x in procs]).value_counts().to_string())
print(json.dumps(cfg))
