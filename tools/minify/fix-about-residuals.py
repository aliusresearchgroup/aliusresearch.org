"""A5 remainder: complete /about/ linkification + fix the Weebly Jackendoff
span split + fix the double-encoded Moreau apostrophe URL.

Surgical find-and-replace against known strings on the About page. Safe to
re-run.
"""
import re
from pathlib import Path
from urllib.parse import quote_plus

REPO = Path(__file__).resolve().parents[2]
ABOUT_DIR = REPO / "site-src" / "content" / "about"

SCHOLAR = "https://scholar.google.com/scholar?q="


def scholar_link(authors: str, year: str) -> str:
    q = f'"{authors} {year}"'
    href = SCHOLAR + quote_plus(q)
    return f'<a class="ref-link" href="{href}" target="_blank" rel="noopener">{authors} {year}</a>'


# Literal fixes — deliberately stable strings we find verbatim in the About
# page so the script is self-contained and doesn't depend on regex parsing the
# surrounding Weebly markup.
FIXES: list[tuple[str, str]] = [
    # 1) Merge <span>Jac</span><font>kendoff …</font> back into plain "Jackendoff"
    (
        '<span style="color:rgb(81, 81, 81)">Jac</span><font color="#515151" style="color:rgb(81, 81, 81)">kendoff 1987; Baars 2003; Marti et al. 2010)',
        'Jackendoff 1987; Baars 2003; Marti et al. 2010)',
    ),
    # 2) Linkify Jackendoff 1987 / Baars 2003 / Marti et al. 2010 inside that same sentence
    (
        'Jackendoff 1987; Baars 2003; Marti et al. 2010)',
        f'{scholar_link("Jackendoff", "1987")}; {scholar_link("Baars", "2003")}; {scholar_link("Marti et al.", "2010")})',
    ),
    # 3) Linkify Maupertuis 1752; Moreau 1845 (left un-linked by earlier regex)
    (
        'Maupertuis 1752; Moreau 1845;',
        f'{scholar_link("Maupertuis", "1752")}; {scholar_link("Moreau", "1845")};',
    ),
    # 4) Fix the Moreau title URL (double-encoded `&rsquo;` / `&eacute;`)
    (
        'https://scholar.google.com/scholar?q=%22Du+Hachisch+et+de+L%26rsquo%3Bali%26eacute%3Bnation+Mentale%22',
        'https://scholar.google.com/scholar?q=%22Du+Hachisch+et+de+L%27ali%C3%A9nation+Mentale%22',
    ),
    # 5) Linkify Corlett/Frith/Fletcher 2009 — right now only "Fletcher 2009" links
    (
        'Corlett, Frith, and <a class="ref-link" href="https://scholar.google.com/scholar?q=%22Fletcher+2009%22" target="_blank" rel="noopener">Fletcher 2009</a>',
        scholar_link("Corlett, Frith, and Fletcher", "2009"),
    ),
    # 6) Linkify Studerus, Gamma, and Vollenweider 2010 (currently only Vollenweider links)
    (
        'Studerus, Gamma, and <a class="ref-link" href="https://scholar.google.com/scholar?q=%22Vollenweider+2010%22" target="_blank" rel="noopener">Vollenweider 2010</a>',
        scholar_link("Studerus, Gamma, and Vollenweider", "2010"),
    ),
    # 7) Linkify Hobson, Pace-Schott, and Stickgold 2000 (currently only Stickgold links)
    (
        'Hobson, Pace-Schott, and <a class="ref-link" href="https://scholar.google.com/scholar?q=%22Stickgold+2000%22" target="_blank" rel="noopener">Stickgold 2000</a>',
        scholar_link("Hobson, Pace-Schott, and Stickgold", "2000"),
    ),
]


def process(text: str) -> tuple[str, int]:
    n = 0
    for find, replace in FIXES:
        if find in text:
            text = text.replace(find, replace)
            n += 1
    return text, n


def main():
    for fname in ("body.html", "original.rewritten.html", "original.html"):
        path = ABOUT_DIR / fname
        if not path.exists():
            continue
        orig = path.read_text(encoding="utf-8-sig", errors="replace")
        new, n = process(orig)
        if n:
            path.write_text(new, encoding="utf-8")
            print(f"  {fname}: applied {n} fixes")
        else:
            print(f"  {fname}: no change (already applied)")


if __name__ == "__main__":
    main()
