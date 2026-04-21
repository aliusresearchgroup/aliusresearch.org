"""Flatten the Bulletin / Events / Membership dropdown menus across all content
files (they become direct links). Team is already handled by update-team-nav.py.

Finds each top-level <li id="pg..."> with one of the known Bulletin/Events/
Membership IDs, removes its nested dropdown, and swaps the href to the new
consolidated canonical URL.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "site-src" / "content"

# (pg_id, link_title, new_href)
FLATTEN_ITEMS = [
    ("pg388209027172883656", "Bulletin",   "/bulletin/"),
    ("pg649956180932632823", "Events",     "/events/"),
    ("pg662395399792559095", "Membership", "/membership/"),
]


def find_li_end(text: str, li_start: int) -> int:
    depth = 1
    end_open = text.find(">", li_start)
    if end_open == -1:
        return -1
    i = end_open + 1
    while i < len(text):
        nxt_open = text.find("<li", i)
        nxt_close = text.find("</li>", i)
        if nxt_close == -1:
            return -1
        if nxt_open != -1 and nxt_open < nxt_close:
            if text[nxt_open:nxt_open + 4] in ("<li ", "<li>"):
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


def flatten_one(text: str, pg_id: str, title: str, href: str) -> tuple[str, int]:
    pattern = re.compile(rf'<li\s+id="{pg_id}"[^>]*class="wsite-menu-item-wrap"[^>]*>', re.IGNORECASE)
    replacement = (
        f'<li id="{pg_id}" class="wsite-menu-item-wrap">'
        f'<a href="{href}" class="wsite-menu-item">{title}</a>'
        '</li>'
    )
    out: list[str] = []
    idx = 0
    count = 0
    for m in pattern.finditer(text):
        start = m.start()
        end = find_li_end(text, start)
        if end == -1:
            continue
        out.append(text[idx:start])
        out.append(replacement)
        idx = end
        count += 1
    if count == 0:
        return text, 0
    out.append(text[idx:])
    return "".join(out), count


def process(text: str) -> tuple[str, int]:
    total = 0
    for pg_id, title, href in FLATTEN_ITEMS:
        text, count = flatten_one(text, pg_id, title, href)
        total += count
    return text, total


def main():
    total_files = 0
    total_replacements = 0
    files_changed = 0
    patterns = ["body.html", "original.rewritten.html", "original.html"]
    for pattern in patterns:
        for path in CONTENT.rglob(pattern):
            total_files += 1
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
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
    print(f"Dropdown flattenings: {total_replacements}")


if __name__ == "__main__":
    main()
