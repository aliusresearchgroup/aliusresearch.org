"""Scoped typography + layout refresh for the /about/ page.

Adds a <style> block that:
- Constrains body copy to 66ch max-width for comfortable reading
- Increases line-height and paragraph spacing
- Makes long <br><br> blocks render like real paragraphs
- Left-aligns body text (the Weebly default is often justified/centered)

Does NOT touch the site header, nav, or any content — strictly presentational
scoping via body.wsite-page-about.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ABOUT_DIR = REPO / "site-src" / "content" / "about"

STYLE_BLOCK = """<style>
/* /about/ page: reading-optimised typography (scoped via body class) */
body.wsite-page-about #wsite-content .wsite-section-elements {
  max-width: 72ch;
  margin: 0 auto;
  padding: 0 24px;
}
body.wsite-page-about #wsite-content .wsite-content-title {
  font-size: 30px !important;
  font-weight: 700 !important;
  color: #1a4d2e !important;
  margin-bottom: 32px !important;
  text-align: left !important;
  letter-spacing: -0.01em !important;
}
body.wsite-page-about #wsite-content .paragraph,
body.wsite-page-about #wsite-content p {
  font-size: 16px !important;
  line-height: 1.72 !important;
  text-align: left !important;
  color: #2a3330 !important;
}
/* Render <br><br> as real paragraph spacing */
body.wsite-page-about #wsite-content .paragraph br + br {
  line-height: 1.6;
  display: block;
  content: "";
  margin-top: 14px;
}
body.wsite-page-about #wsite-content .paragraph > br {
  content: "";
  display: block;
  margin-top: 0;
}
/* Distinct in-text citation links (already inserted by linkify-about-references.py) */
body.wsite-page-about .ref-link {
  color: #1a4d2e !important;
  border-bottom: 1px dotted #3d8b3d !important;
  transition: color 120ms ease, border-bottom-color 120ms ease !important;
  text-decoration: none !important;
}
body.wsite-page-about .ref-link:hover {
  border-bottom-style: solid !important;
  color: #0f1a11 !important;
}
/* Narrow screens */
@media (max-width: 640px) {
  body.wsite-page-about #wsite-content .wsite-section-elements {
    padding: 0 16px;
  }
  body.wsite-page-about #wsite-content .paragraph,
  body.wsite-page-about #wsite-content p {
    font-size: 15px !important;
    line-height: 1.65 !important;
  }
}
</style>
"""

MARKER = "/about/ page: reading-optimised typography"


def process(text: str) -> str:
    if MARKER in text:
        # Re-inject (update) — strip old block first
        text = re.sub(
            r'<style>\s*/\* ' + re.escape(MARKER) + r'[\s\S]*?</style>\s*',
            '',
            text,
        )
    if "</head>" in text:
        return text.replace("</head>", STYLE_BLOCK + "</head>", 1)
    return STYLE_BLOCK + text


def main():
    for fname in ("body.html", "original.rewritten.html", "original.html"):
        path = ABOUT_DIR / fname
        if not path.exists():
            continue
        orig = path.read_text(encoding="utf-8-sig", errors="replace")
        new = process(orig)
        if new != orig:
            path.write_text(new, encoding="utf-8")
            print(f"  {fname}: updated")


if __name__ == "__main__":
    main()
