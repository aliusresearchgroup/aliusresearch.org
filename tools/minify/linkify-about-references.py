"""Turn in-text academic citations and italic paper/book titles on /about/
into clickable links to a Google Scholar search for that reference.

Safe transforms — idempotent (won't double-wrap) — on site-src/content/about/
body.html + original.rewritten.html + original.html.

Transforms:
1. "(Smith 2020)" / "(Smith, 2020)" / "(Smith and Jones 2020)" /
   "(Smith et al. 2020)" / multi-cite "(A 2020; B 2019; C 2018)":
   Each author-year unit becomes an <a> that searches Scholar for
   `"<author> <year>"`. Compound cites are split on ';' and each piece
   linked independently.
2. Italic passages (<em>...</em>, <i>...</i>, <font style="...italic...">)
   that look like titles (20-200 chars, plausible title capitalisation) become
   Scholar search links for that exact title.

The citation/title link uses `class="ref-link"` so CSS can style them
consistently (subtle green underline to match ALIUS palette).
"""
import re
from pathlib import Path
from urllib.parse import quote_plus

REPO = Path(__file__).resolve().parents[2]
ABOUT_DIR = REPO / "site-src" / "content" / "about"

SCHOLAR_BASE = "https://scholar.google.com/scholar?q="

# Citation pattern: a surname (possibly hyphenated), optional "et al.", optional
# "and X", optional comma, then a 4-digit year. Does NOT cross parenthesis
# boundaries — we match INSIDE the parens.
AUTHOR_YEAR_RE = re.compile(
    r"""(
      [A-ZÀ-Ý][a-zà-ÿ\-']+                      # First surname
      (?:\s+(?:and|&)\s+[A-ZÀ-Ý][a-zà-ÿ\-']+)?  # optional "and Jones"
      (?:,?\s+[A-ZÀ-Ý][a-zà-ÿ\-']+)*            # optional ", Smith, Chen"
      (?:\s+et\s+al\.?)?                         # optional "et al."
    )                                            # group 1 = authors
    (?:,?\s+)                                    # comma or space
    ((?:19|20)\d{2}[a-z]?)                       # group 2 = year
    """,
    re.VERBOSE,
)

PAREN_CITE_RE = re.compile(r'\(((?:[^()]{5,500}?))\)')


def wrap_citation(match: re.Match) -> str:
    inner = match.group(1)
    # If there's no 4-digit year inside, leave the parens alone.
    if not re.search(r'(19|20)\d{2}', inner):
        return match.group(0)
    # Skip if this parens already contains <a> tags (idempotency)
    if '<a ' in inner or 'ref-link' in inner:
        return match.group(0)
    # Also skip trivial like "(e.g.)" or "(p. 20)" with no year, already handled
    # Skip if inner contains HTML formatting beyond simple text (to avoid
    # mangling markup inside parens)
    if re.search(r'<(?!br\b)[a-z]+\b', inner, re.IGNORECASE):
        return match.group(0)

    # Split on ';' to separate multiple citations, but remember separators
    parts = re.split(r'(\s*;\s*)', inner)
    out_parts = []
    modified = False
    for p in parts:
        if re.fullmatch(r'\s*;\s*', p):
            out_parts.append(p)
            continue
        # Try to find ONE author-year unit in this piece (may be prefaced by
        # "see", "cf.", "e.g.,", etc. which we preserve verbatim before the link).
        m = AUTHOR_YEAR_RE.search(p)
        if not m:
            out_parts.append(p)
            continue
        authors = m.group(1).strip()
        year = m.group(2)
        prefix = p[: m.start()]
        suffix = p[m.end() :]
        query = f'"{authors} {year}"'
        href = SCHOLAR_BASE + quote_plus(query)
        link = f'<a class="ref-link" href="{href}" target="_blank" rel="noopener">{authors} {year}</a>'
        out_parts.append(prefix + link + suffix)
        modified = True
    if not modified:
        return match.group(0)
    return '(' + ''.join(out_parts) + ')'


# Italic title: <em>Title</em>, <i>Title</i>, <font style="... italic ...">Title</font>
# We only transform when the italic content is >= 15 chars and doesn't already
# contain a link.
ITAL_RE = re.compile(
    r"""(
      <em[^>]*>|<i[^>]*>|<font[^>]*style\s*=\s*"[^"]*italic[^"]*"[^>]*>
    )
    (?!\s*<a\b)                                   # not already containing a link
    ([^<]{15,200}?)
    (
      </em>|</i>|</font>
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def wrap_italic(match: re.Match) -> str:
    opener, body, closer = match.group(1), match.group(2), match.group(3)
    title = re.sub(r'\s+', ' ', body).strip()
    # Skip obvious non-titles: single lowercase words, author names with years
    if not title or title.lower() in ("ibid", "e.g.", "i.e.", "see", "cf."):
        return match.group(0)
    if re.fullmatch(r'[a-z\s]+', title) and len(title) < 30:
        return match.group(0)
    # Skip if title is really an email or author-year (already handled by cite)
    if '[at]' in title or '[dot]' in title or '@' in title:
        return match.group(0)
    if re.fullmatch(AUTHOR_YEAR_RE.pattern, title, re.VERBOSE):
        return match.group(0)
    href = SCHOLAR_BASE + quote_plus(f'"{title}"')
    link = f'<a class="ref-link" href="{href}" target="_blank" rel="noopener">{body}</a>'
    return opener + link + closer


STYLE_BLOCK = """<style>
/* About-page: in-text reference links (citations + italic titles) */
body.wsite-page-about .ref-link,
body .wsite-section-elements .ref-link {
  color: inherit !important;
  text-decoration: none !important;
  border-bottom: 1px dotted #3d8b3d !important;
  padding-bottom: 0 !important;
  transition: color 120ms ease, border-bottom-color 120ms ease !important;
}
body.wsite-page-about .ref-link:hover,
body .wsite-section-elements .ref-link:hover {
  color: #1a4d2e !important;
  border-bottom: 1px solid #1a4d2e !important;
}
</style>
"""


def process(text: str) -> str:
    # 1) Wrap author-year inside parens
    new = PAREN_CITE_RE.sub(wrap_citation, text)
    # 2) Wrap italic titles
    new = ITAL_RE.sub(wrap_italic, new)
    # 3) Inject style block (idempotent)
    if "ref-link" not in new:
        return new
    if "About-page: in-text reference links" in new:
        return new
    if "</head>" in new:
        new = new.replace("</head>", STYLE_BLOCK + "</head>", 1)
    else:
        new = STYLE_BLOCK + new
    return new


def main():
    for fname in ("body.html", "original.rewritten.html", "original.html"):
        path = ABOUT_DIR / fname
        if not path.exists():
            continue
        orig = path.read_text(encoding="utf-8-sig", errors="replace")
        new = process(orig)
        if new == orig:
            print(f"  {fname}: no change")
            continue
        # Count how many ref-links we added (diff vs original)
        added = new.count('class="ref-link"') - orig.count('class="ref-link"')
        path.write_text(new, encoding="utf-8")
        print(f"  {fname}: {added} references linkified")


if __name__ == "__main__":
    main()
