"""Inject a site-wide scoped CSS block to address audit items A13 + A14:

  A13 · Palette-lock consolidated-page heading colours. Today pages mix
        `#156138`, `rgb(81,81,81)`, `rgb(123,140,137)`, `#42514c` competing
        on the same page. Collapse to ALIUS: `#1a4d2e` / `#3d8b3d` / `#6b7571`.

  A14 · Bulletin interview pages render in a ~60% centre column inside a 14-col
        Weebly table (14/72/14 %). Replace with a constrained single-column
        reading width (max 72ch, left-aligned) via CSS override.

Injected once into every built HTML via the existing partial include path.
Idempotent — if the block's marker is already present, we skip.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

STYLE_BLOCK = """<style>
/* Site refresh — palette lock (A13) + reading-column (A14) */
.wsite-page-bulletin #wsite-content h2,
.wsite-page-bulletin #wsite-content h2 *,
.wsite-page-events #wsite-content h2,
.wsite-page-events #wsite-content h2 *,
.wsite-page-membership #wsite-content h2,
.wsite-page-membership #wsite-content h2 * {
  color: #1a4d2e !important;
}
.wsite-page-bulletin #wsite-content .wsite-content-title font,
.wsite-page-events #wsite-content .wsite-content-title font,
.wsite-page-membership #wsite-content .wsite-content-title font {
  color: inherit !important;
}
/* Section-divider sub-headings */
.wsite-page-bulletin #wsite-content .wsite-section-wrap + .wsite-section-wrap h2 strong,
.wsite-page-events #wsite-content .wsite-section-wrap + .wsite-section-wrap h2 strong,
.wsite-page-membership #wsite-content .wsite-section-wrap + .wsite-section-wrap h2 strong {
  color: #3d8b3d !important;
}

/* ---- A14 · Bulletin-interview reading column ---- */
body[class*="wsite-page-bulletin"] #wsite-content .wsite-multicol-table-wrap,
body[class*="wsite-page-bulletin"] #wsite-content .wsite-multicol-table,
body[class*="wsite-page-bulletin"] #wsite-content .wsite-multicol-tbody,
body[class*="wsite-page-bulletin"] #wsite-content .wsite-multicol-tr {
  display: block !important;
  width: 100% !important;
  margin: 0 auto !important;
}
body[class*="wsite-page-bulletin"] #wsite-content .wsite-multicol-col {
  display: block !important;
  width: auto !important;
  max-width: 72ch !important;
  margin: 0 auto !important;
  padding: 0 24px !important;
  text-align: left !important;
}
body[class*="wsite-page-bulletin"] #wsite-content .paragraph,
body[class*="wsite-page-bulletin"] #wsite-content p {
  text-align: left !important;
  line-height: 1.68 !important;
  font-size: 16px !important;
}
body[class*="wsite-page-bulletin"] #wsite-content img {
  max-width: 100% !important;
  height: auto !important;
}
/* Keep existing styling on the consolidated /bulletin/ landing — only the
   interior interview pages should pick up the 72ch column; the landing has
   its own section-nav and grid */
body.wsite-page-bulletin #wsite-content .wsite-multicol-col {
  max-width: none !important;
  padding: 0 !important;
}
</style>
"""

MARKER = "Site refresh — palette lock (A13) + reading-column (A14)"


def process(text: str) -> str:
    if MARKER in text:
        return text
    if "</head>" in text:
        return text.replace("</head>", STYLE_BLOCK + "</head>", 1)
    return text


def main():
    total = changed = 0
    for root in [REPO / "site-src" / "content", REPO / "docs"]:
        if not root.exists():
            continue
        for path in root.rglob("*.html"):
            total += 1
            try:
                orig = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            new = process(orig)
            if new != orig:
                path.write_text(new, encoding="utf-8")
                changed += 1
    print(f"Scanned {total} files; injected refresh CSS into {changed}")


if __name__ == "__main__":
    main()
