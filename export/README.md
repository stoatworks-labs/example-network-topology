# Documentation exports

Standalone, offline-readable versions of every design doc, regenerated from the
markdown sources (`README.md` + `docs/*.md`) — do not edit these directly.

- [`html/`](html/) — one self-contained HTML file per doc (embedded styling, diagrams
  inlined) plus `full-documentation.html`, everything in one file. `index.html` is the
  repo README.
- [`pdf/`](pdf/) — the same set as A4 PDFs, plus `full-documentation.pdf` (the whole
  design as one printable document).

Links between docs work within `html/`; links to `config/` files point at the GitHub
repo, since configs aren't part of the export.
