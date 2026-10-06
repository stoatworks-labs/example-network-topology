#!/usr/bin/env python3
"""Regenerate export/html/ and export/pdf/ from README.md + docs/*.md.

    python3 export/build.py            # HTML + PDF
    python3 export/build.py --html     # HTML only

Needs pandoc on PATH, and for PDFs Node with Playwright's Chromium. Run
diagrams/generate.py first if any diagram changed: README images are inlined from
diagrams/*.svg at build time.

Links between docs become links between the exported files; links into config/ or
diagrams/ point at the GitHub repo (derived from `git remote get-url origin`), since
those aren't part of the export.
"""

import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "export" / "html"
PDF_DIR = ROOT / "export" / "pdf"

# Reading order for full-documentation.{html,pdf}; any doc not listed is appended.
ORDER = [
    "README", "topology", "server-specification", "ip-address-map", "streaming-flow",
    "birddog-play-rationale", "gl-inet-rationale", "live-editing", "file-sync-flow",
    "atem-iso-ingest", "vmix-record-ingest", "glkvm-cloud", "bandwidth-analysis",
    "tailscale", "open-questions", "topology-alternative-tailscale-switches",
    "deployment-runbook", "troubleshooting",
]
SKIP = {"NOTES"}  # working notes, not design documentation

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial,
       sans-serif; font-size: 16px; line-height: 1.55; color: #1f2328;
       max-width: 900px; margin: 0 auto; padding: 2rem 1.5rem 4rem; background: #fff; }
h1, h2, h3, h4 { line-height: 1.25; margin-top: 1.6em; margin-bottom: .6em;
       font-weight: 650; }
h1 { font-size: 2em; border-bottom: 1px solid #d1d9e0; padding-bottom: .3em; }
h2 { font-size: 1.45em; border-bottom: 1px solid #d1d9e0; padding-bottom: .3em; }
h3 { font-size: 1.2em; }
a { color: #0969da; text-decoration: none; }
a:hover { text-decoration: underline; }
code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
       monospace; font-size: .85em; background: #f0f2f5; padding: .15em .35em;
       border-radius: 4px; }
pre { background: #f6f8fa; border: 1px solid #e3e8ee; border-radius: 6px;
      padding: 14px; overflow-x: auto; line-height: 1.4; }
pre code { background: none; padding: 0; font-size: .8em; }
table { border-collapse: collapse; margin: 1em 0; display: block; overflow-x: auto;
        max-width: 100%; }
th, td { border: 1px solid #d1d9e0; padding: 6px 12px; text-align: left;
         vertical-align: top; }
th { background: #f6f8fa; font-weight: 650; }
tr:nth-child(even) td { background: #fafbfc; }
blockquote { border-left: 4px solid #d1d9e0; margin: 1em 0; padding: 0 1em;
             color: #59636e; }
img, svg { max-width: 100%; height: auto; }
figure { margin: 1.5em 0; }
figcaption { color: #59636e; font-size: .85em; margin-top: .4em; }
hr { border: none; border-top: 2px solid #e3e8ee; margin: 2em 0; }
ul.task-list { list-style: none; padding-left: 1.2em; }
.doc-meta { color: #59636e; font-size: .85em; border-bottom: 2px solid #e3e8ee;
            padding-bottom: .8em; margin-bottom: 1.5em; }
.doc-section { page-break-before: always; }
.doc-section:first-of-type { page-break-before: avoid; }
@media print {
  body { font-size: 10.5pt; max-width: none; padding: 0; }
  pre { white-space: pre; overflow-x: hidden; }
  pre code { font-size: 7.4pt; }
  table { display: table; width: 100%; overflow-wrap: break-word;
          font-size: 8pt; }
  th, td { padding: 3px 6px; }
  a { color: #1f2328; }
  h1, h2, h3 { page-break-after: avoid; }
  pre, img, svg, figure { page-break-inside: avoid; }
}
@page { size: A4; margin: 15mm 13mm; }
"""


def repo_url():
    url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                         capture_output=True, text=True, check=True).stdout.strip()
    m = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        sys.exit(f"can't derive a GitHub repo from origin {url!r}")
    return "https://github.com/" + m[1]


def sources():
    docs = {"README": ROOT / "README.md"}
    for p in sorted((ROOT / "docs").glob("*.md")):
        if p.stem not in SKIP:
            docs[p.stem] = p
    order = [d for d in ORDER if d in docs] + sorted(d for d in docs if d not in ORDER)
    return [(d, docs[d]) for d in order]


def out_name(stem):
    return "index" if stem == "README" else stem


def inline_images(md, src):
    """Replace ![alt](diagrams/x.svg) with the SVG itself so exports are self-contained."""
    def sub(m):
        alt, target = m[1], m[2]
        path = (src.parent / target).resolve()
        if path.suffix != ".svg" or not path.exists():
            return m[0]
        svg = path.read_text()
        svg = re.sub(r"^<\?xml[^>]*>\s*", "", svg)
        return (f'\n\n<figure role="img" aria-label="{html.escape(alt)}">{svg}'
                f"<figcaption>{html.escape(alt)}</figcaption></figure>\n\n")
    return re.sub(r"!\[([^\]]*)\]\(([^)\s]+\.svg)\)", sub, md)


def pandoc(md):
    return subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", "--wrap=none"],
                          input=md, capture_output=True, text=True, check=True).stdout


def rewrite_links(body, src, gh, single):
    """Point doc links at exported files (or #anchors in the combined file)."""
    stems = {p.resolve(): s for s, p in sources()}

    def sub(m):
        href = m[1]
        if re.match(r"[a-z]+:|#", href):
            return m[0]
        path_part, _, frag = href.partition("#")
        target = (src.parent / path_part).resolve()
        if target in stems:
            stem = stems[target]
            if single:
                return f'href="#{frag or "doc-" + out_name(stem)}"'
            return f'href="{out_name(stem)}.html{"#" + frag if frag else ""}"'
        rel = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else path_part
        kind = "tree" if target.is_dir() else "blob"
        return f'href="{gh}/{kind}/main/{rel}{"#" + frag if frag else ""}"'
    return re.sub(r'href="([^"]*)"', sub, body)


def page(title, body):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
            f"<body>{body}</body></html>\n")


def title_of(md):
    m = re.search(r"^# (.+)$", md, re.M)
    return re.sub(r"[*_`]", "", m[1]).strip() if m else "Untitled"


def build_html():
    gh = repo_url()
    name = gh.rsplit("/", 1)[1]
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    combined, toc = [], []
    for stem, src in sources():
        md = inline_images(src.read_text(), src)
        title = title_of(md)
        body = pandoc(md)
        rel = src.relative_to(ROOT).as_posix()
        meta = (f'<div class="doc-meta">Standalone export of <code>{rel}</code> from '
                f'<a href="{gh}">{name}</a></div>')
        (HTML_DIR / f"{out_name(stem)}.html").write_text(
            page(title, meta + rewrite_links(body, src, gh, single=False)))
        anchor = "doc-" + out_name(stem)
        toc.append(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>')
        combined.append(f'<section class="doc-section" id="{anchor}">'
                        f"{rewrite_links(body, src, gh, single=True)}</section>")
    (HTML_DIR / "full-documentation.html").write_text(page(
        f"{name} — full documentation",
        f"<h1>{name} — full documentation</h1><ul>{''.join(toc)}</ul>{''.join(combined)}"))
    print(f"html: {len(toc) + 1} files")


PDF_JS = r"""
const { chromium } = require(process.env.PW || 'playwright');
(async () => {
  const [inDir, outDir, names] = [process.argv[2], process.argv[3], JSON.parse(process.argv[4])];
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const n of names) {
    await page.goto('file://' + inDir + '/' + n + '.html', { waitUntil: 'load' });
    await page.pdf({ path: outDir + '/' + (n === 'index' ? 'README' : n) + '.pdf',
                     format: 'A4', printBackground: true, preferCSSPageSize: true });
  }
  await browser.close();
})();
"""


def build_pdf():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    names = [p.stem for p in sorted(HTML_DIR.glob("*.html"))]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(PDF_JS)
    env = None
    pw = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    if pw:
        env = dict(os.environ, PW=str(Path(pw) / "playwright"))
    subprocess.run(["node", f.name, str(HTML_DIR), str(PDF_DIR), json.dumps(names)],
                   check=True, env=env)
    print(f"pdf: {len(names)} files")


if __name__ == "__main__":
    build_html()
    if "--html" not in sys.argv:
        build_pdf()
