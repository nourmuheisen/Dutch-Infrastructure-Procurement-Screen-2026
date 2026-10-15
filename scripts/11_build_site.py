"""Builds the website: injects site/data.json into site/src.html.

Outputs
  docs/index.html   standalone page: data, map and fonts inside; GitHub Pages serves /docs
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
src = (SITE / "src.html").read_text()
data = (SITE / "data.json").read_text().replace("</", "<\\/")
# fonts: inline the woff2 files (SIL Open Font License) so the page works offline
import base64, re
FACES = [("Barlow", 400, "normal", "barlow-latin-400-normal"), ("Barlow", 500, "normal", "barlow-latin-500-normal"),
         ("Barlow", 600, "normal", "barlow-latin-600-normal"), ("Barlow", 400, "italic", "barlow-latin-400-italic"),
         ("Barlow Condensed", 500, "normal", "barlow-condensed-latin-500-normal"),
         ("Barlow Condensed", 600, "normal", "barlow-condensed-latin-600-normal"),
         ("Barlow Condensed", 700, "normal", "barlow-condensed-latin-700-normal"),
         ("IBM Plex Mono", 400, "normal", "ibm-plex-mono-latin-400-normal"),
         ("IBM Plex Mono", 500, "normal", "ibm-plex-mono-latin-500-normal")]
css = "".join(
    f"@font-face{{font-family:'{fam}';font-style:{st};font-weight:{wt};font-display:swap;"
    f"src:url(data:font/woff2;base64,{base64.b64encode((SITE / 'fonts' / (fn + '.woff2')).read_bytes()).decode()}) format('woff2')}}"
    for fam, wt, st, fn in FACES)
src = re.sub(r'<link rel="preconnect"[^>]*>\n', "", src)
src = re.sub(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>\n', "", src)
src = src.replace("<style>", "<style>" + css + "\n", 1)
page = src.replace("__DATA__", data)
head, _, rest = page.partition("</style>")
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       + head + "</style>\n</head>\n<body>\n" + rest + "\n</body>\n</html>\n")
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)
(DOCS / "index.html").write_text(doc)  # GitHub Pages serves /docs
print("built", round(len(doc) / 1024), "KB")
