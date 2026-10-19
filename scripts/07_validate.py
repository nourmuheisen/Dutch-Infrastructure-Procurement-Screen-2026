"""Phase 5: validation.

1. Field-level comparison of pipeline records against the official TenderNed notice PDFs
   (18 shortlist lead notices + 8 randomly drawn others, random_state=42).
2. Rule-versus-review agreement for the capability scores.
3. Contract values recovered from the PDFs (placeholders < EUR 1,000 treated as missing).

Output: data/validation_results.csv, data/validation_summary.json
"""
import json, re, unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
v = pd.read_csv(DATA / "validation_pdf_extracts.csv", dtype=str).fillna("")
m = pd.read_csv(DATA / "master_dataset.csv", dtype=str).fillna("")
p = pd.read_csv(DATA / "phase1_projects.csv", dtype=str).fillna("")
notices = pd.read_csv(DATA / "notices_all.csv", dtype=str).fillna("").set_index("publicatieId")
rec = p.set_index("latest_notice_id")

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

TYPE_FAMILY = {"AAO": "competition", "REC": "competition", "VAK": "prior", "MAC": "prior",
               "AGO": "result", "AAW": "modification", "VBE": "result"}
def pdf_family(t):
    t = t.lower()
    if "modification" in t: return "modification"
    if "result" in t or "award" in t: return "result"
    if "prior" in t or "planning" in t: return "prior"
    if "competition" in t or "contract notice" in t: return "competition"
    return "?"

rows = []
for _, r in v.iterrows():
    x = rec.loc[r.notice_id]
    n = notices.loc[r.notice_id]
    title_sim = SequenceMatcher(None, norm(x.title), norm(r.pdf_title)).ratio()
    auth_ok = norm(r.pdf_authority).startswith(norm(x.authority)[:25]) or norm(x.authority).startswith(norm(r.pdf_authority)[:25])
    date_diff = (abs((pd.Timestamp(n.publicatieDatum) - pd.Timestamp(r.pdf_publication_date)).days)
                 if r.pdf_publication_date else None)
    # type: compare the notice's own listing type with the PDF form family
    lt = n.typePublicatie
    fam_pipe = TYPE_FAMILY.get(lt, "?")
    fam_pdf = pdf_family(r.pdf_notice_type)
    if lt == "REC":  # a rectification is published on the form of the notice it corrects
        type_ok = True
    elif lt == "VBE":
        type_ok = fam_pdf in ("result", "?")
    else:
        type_ok = fam_pipe == fam_pdf
    cpv_ok = x.cpv_main[:8] == r.pdf_main_cpv[:8]
    pipe_nuts = set(c for c in x.nuts_codes.split(";") if c and c != "NL")
    pdf_nuts = set(re.findall(r"NL\d{2,3}[A-Z]?", r.pdf_nuts))
    if not pipe_nuts:
        nuts_ok = "n/a (pipeline national)"
    elif not pdf_nuts:
        nuts_ok = "n/a (PDF gives place name only)"
    else:
        nuts_ok = "match" if (pipe_nuts & pdf_nuts or any(pn.startswith(pp) or pp.startswith(pn) for pn in pdf_nuts for pp in pipe_nuts)) else "MISMATCH"
    val = float(r.pdf_value_eur) if r.pdf_value_eur else None
    rows.append({
        "notice_id": r.notice_id, "sample": r.loc["sample"], "title": x.title,
        "title_similarity": round(title_sim, 3), "title_ok": title_sim >= 0.9,
        "authority_ok": auth_ok, "pub_date_diff_days": date_diff,
        "notice_type_ok": type_ok, "cpv_main_ok": cpv_ok, "nuts_check": nuts_ok,
        "pdf_value_eur": val if val and val >= 1000 else None,
        "value_placeholder_in_pdf": bool(val is not None and val < 1000),
        "pdf_winners": r.pdf_winners or None, "pdf_note": r.pdf_note or None,
    })
res = pd.DataFrame(rows)
res.to_csv(DATA / "validation_results.csv", index=False)

# ---- rule vs review agreement --------------------------------------------------------
CAPS = ["investment_planning", "procurement_commercial", "controls_assurance", "asset_lifecycle"]
agree = {}
for c in CAPS:
    d = (m[c].astype(float) - m[f"{c}_rule"].astype(float))
    agree[c] = {"unchanged": int((d == 0).sum()), "raised": int((d > 0).sum()), "lowered": int((d < 0).sum()),
                "mean_abs_change": round(float(d.abs().mean()), 2)}
tot = sum(a["unchanged"] for a in agree.values())
summary = {
    "validated_notices": len(res),
    "title_match_rate": round(res.title_ok.mean(), 3),
    "authority_match_rate": round(res.authority_ok.mean(), 3),
    "notice_type_consistency_rate": round(res.notice_type_ok.mean(), 3),
    "cpv_main_match_rate": round(res.cpv_main_ok.mean(), 3),
    "nuts_checks": res.nuts_check.value_counts().to_dict(),
    "pub_date_diff_days": res.pub_date_diff_days.value_counts(dropna=False).to_dict(),
    "pdf_values_recovered": int(res.pdf_value_eur.notna().sum()),
    "pdf_value_placeholders": int(res.value_placeholder_in_pdf.sum()),
    "rule_review_agreement_overall": round(tot / (len(m) * len(CAPS)), 3),
    "rule_review_by_capability": agree,
}
(DATA / "validation_summary.json").write_text(json.dumps(summary, indent=2, default=str))
print(json.dumps(summary, indent=2, default=str))
print(res[~(res.title_ok & res.authority_ok & res.notice_type_ok & res.cpv_main_ok)]
      [["notice_id", "title_similarity", "authority_ok", "notice_type_ok", "cpv_main_ok", "nuts_check"]].to_string())
