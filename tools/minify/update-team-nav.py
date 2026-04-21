"""Replace the Team dropdown menu across all content HTML with a direct link to /team/.

Operates on:
- site-src/content/**/body.html
- site-src/content/**/original.rewritten.html
- site-src/content/**/original.html

For each file, finds the Team <li> menu item (by pg714570715415488939 id) and
its following dropdown <div class="wsite-menu-wrap">...</div>, and replaces the
entire block with a minimal <li> containing just a direct link.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "site-src" / "content"

# Match the full Team <li>...</li> block, INCLUDING its nested dropdown div.
# The <li> contains the menu anchor, then a <div class="wsite-menu-wrap"> with
# sub-items, then closes </li>. We need to balance depth of <div> nesting.

TEAM_LI_START_RE = re.compile(
    r'<li\s+id="pg714570715415488939"[^>]*class="wsite-menu-item-wrap"[^>]*>',
    re.IGNORECASE,
)


def find_li_end(text: str, li_start: int) -> int:
    """Given the index of a <li ...> opening, return the index just past its </li>."""
    # <li> has no nesting of <li> inside *this* item (sub-items are inside <ul>)
    # but contains <ul>/<div> etc. We track <li> depth.
    depth = 1
    i = li_start
    # Advance past the opening tag
    end_open = text.find(">", i)
    if end_open == -1:
        return -1
    i = end_open + 1
    while i < len(text):
        nxt_open = text.find("<li", i)
        nxt_close = text.find("</li>", i)
        if nxt_close == -1:
            return -1
        if nxt_open != -1 and nxt_open < nxt_close:
            # Check it's really an <li (not <link etc)
            following = text[nxt_open:nxt_open + 4]
            if following in ("<li ", "<li>"):
                depth += 1
                i = nxt_open + 3
                continue
            else:
                i = nxt_open + 1
                continue
        depth -= 1
        if depth == 0:
            return nxt_close + len("</li>")
        i = nxt_close + len("</li>")
    return -1


REPLACEMENT = (
    '<li id="pg714570715415488939" class="wsite-menu-item-wrap">'
    '<a href="/team/" class="wsite-menu-item">Team</a>'
    '</li>'
)


def process(text: str) -> tuple[str, int]:
    replaced = 0
    idx = 0
    out: list[str] = []
    for m in TEAM_LI_START_RE.finditer(text):
        start = m.start()
        end = find_li_end(text, start)
        if end == -1:
            continue
        out.append(text[idx:start])
        out.append(REPLACEMENT)
        idx = end
        replaced += 1
    if replaced == 0:
        return text, 0
    out.append(text[idx:])
    return "".join(out), replaced


def main():
    total_files = 0
    total_replacements = 0
    files_changed = 0
    patterns = ["body.html", "original.rewritten.html", "original.html"]
    for pattern in patterns:
        for path in CONTENT.rglob(pattern):
            total_files += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  ! read failed: {path}: {e}")
                continue
            new_text, count = process(text)
            if count > 0:
                path.write_text(new_text, encoding="utf-8")
                files_changed += 1
                total_replacements += count
    print(f"Scanned: {total_files} files")
    print(f"Changed: {files_changed} files")
    print(f"Team-menu replacements: {total_replacements}")


if __name__ == "__main__":
    main()
