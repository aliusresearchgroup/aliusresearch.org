"""Remove all Ko-fi donation widgets from every content file.

Ko-fi floating-chat widgets are embedded as:
  <div><div id="..." class="wcustomhtml">
    <script src='https://storage.ko-fi.com/...'></script>
    <script>kofiWidgetOverlay.draw('...', {...});</script>
  </div></div>

This script removes:
  1. Any <script> tag whose src references ko-fi.com / storage.ko-fi.com
  2. Any inline <script> block that calls kofiWidgetOverlay
  3. The surrounding .wcustomhtml <div> wrappers if they become empty after
     the scripts are stripped.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOTS = [
    REPO / "site-src" / "content",
    REPO / "docs",
]

# 1) External ko-fi script tags
EXT_SCRIPT_RE = re.compile(
    r'<script\b[^>]*src\s*=\s*["\'][^"\']*ko-?fi\.com[^"\']*["\'][^>]*>\s*</script>\s*',
    re.IGNORECASE | re.DOTALL,
)
# 2) Inline scripts that reference kofiWidgetOverlay
INLINE_SCRIPT_RE = re.compile(
    r'<script\b(?![^>]*src=)[^>]*>(?:(?!</script>).)*?kofi(?:WidgetOverlay)?\b.*?</script>\s*',
    re.IGNORECASE | re.DOTALL,
)
# 3) Empty wcustomhtml wrappers that are left behind
EMPTY_WCUSTOM_RE = re.compile(
    r'<div><div\s+id="\d+"[^>]*class="wcustomhtml"[^>]*>\s*</div></div>\s*',
    re.IGNORECASE | re.DOTALL,
)
# 4) Ko-fi iframe widgets
KOFI_IFRAME_RE = re.compile(
    r'<iframe\b[^>]*(?:id\s*=\s*["\']kofiframe["\']|src\s*=\s*["\'][^"\']*ko-?fi\.com[^"\']*["\'])[^>]*>\s*</iframe>\s*',
    re.IGNORECASE | re.DOTALL,
)
# 5) wcustomhtml wrappers that contain a Ko-fi iframe (strip the wrapper too)
KOFI_WRAPPER_RE = re.compile(
    r'<div\s*>\s*<div\s+id="\d+"[^>]*class="wcustomhtml"[^>]*>\s*<iframe\b[^>]*ko-?fi\.com[^>]*>\s*</iframe>\s*</div>\s*</div>\s*',
    re.IGNORECASE | re.DOTALL,
)
# 4) Double-wrapped empty paragraph wrappers
EMPTY_PARA_DIV_RE = re.compile(
    r'<div>\s*<div\s+class="paragraph"[^>]*>\s*</div>\s*</div>\s*',
    re.IGNORECASE | re.DOTALL,
)


def process(text: str) -> tuple[str, int]:
    count = 0
    # Strip ko-fi iframe wrappers (wrapper+iframe as one unit) first so we don't
    # leave orphaned empty wcustomhtml divs behind.
    new, n = KOFI_WRAPPER_RE.subn("", text); count += n
    new, n = KOFI_IFRAME_RE.subn("", new); count += n
    new, n = EXT_SCRIPT_RE.subn("", new); count += n
    new, n = INLINE_SCRIPT_RE.subn("", new); count += n
    if count > 0:
        new, _ = EMPTY_WCUSTOM_RE.subn("", new)
    return new, count


def main():
    total_files = 0
    total_hits = 0
    changed_files = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.html"):
            total_files += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  ! read failed: {path}: {e}")
                continue
            new_text, hits = process(text)
            if hits > 0:
                path.write_text(new_text, encoding="utf-8")
                changed_files += 1
                total_hits += hits
    print(f"Scanned: {total_files} html files")
    print(f"Changed: {changed_files} files")
    print(f"Ko-fi script tags stripped: {total_hits}")


if __name__ == "__main__":
    main()
