"""Post-build: wrap <img src="...png|jpg"> in <picture> with webp <source>.

Idempotent: if the parent element is already a <picture>, skip.
Only wraps when a .webp sibling exists for the image's path (resolved against docs/).

Safe behavior:
- Preserves every original <img ...> attribute (only wraps it)
- Falls back to the original image when browser does not support webp
- Handles URLs with query strings and relative/absolute site paths
"""
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"

# Match <img ...> (self-closing or not). We only wrap <img>s with an src attribute
# containing a .png/.jpg/.jpeg path. We skip data URIs and external URLs.
IMG_RE = re.compile(
    r'<img\b(?P<attrs>[^>]*?)\s*/?>',
    re.IGNORECASE,
)
SRC_RE = re.compile(r'''\bsrc\s*=\s*["'](?P<src>[^"']+)["']''', re.IGNORECASE)


def resolve_webp(html_path: Path, img_src: str) -> Path | None:
    """Given an <img src="...">, return the webp sibling path on disk, or None."""
    # Strip query string and fragment
    parsed = urlparse(img_src)
    if parsed.scheme in ("http", "https", "data"):
        return None
    # Site-absolute vs relative
    path = parsed.path
    if not path:
        return None
    ext = Path(path).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        return None
    if path.startswith("/"):
        local_path = DOCS / path.lstrip("/")
    else:
        local_path = (html_path.parent / path).resolve()
    webp_path = local_path.with_suffix(".webp")
    return webp_path if webp_path.exists() else None


def wrap_imgs_in_html(html: str, html_path: Path) -> tuple[str, int]:
    """Return (new_html, count_wrapped)."""
    count = 0
    out_parts: list[str] = []
    last_end = 0
    for m in IMG_RE.finditer(html):
        start = m.start()
        end = m.end()
        out_parts.append(html[last_end:start])
        img_tag = m.group(0)
        # Skip if the character immediately before this <img> already closes a <source> of a picture
        # or more robustly, check if the enclosing is <picture>...</picture>.
        # We do a lookback: find the last <picture or </picture before this <img>.
        lookback = html[max(0, start - 200):start]
        last_picture_open = lookback.rfind("<picture")
        last_picture_close = lookback.rfind("</picture>")
        if last_picture_open > last_picture_close:
            # Already inside a <picture>
            out_parts.append(img_tag)
            last_end = end
            continue
        src_m = SRC_RE.search(m.group("attrs"))
        if not src_m:
            out_parts.append(img_tag)
            last_end = end
            continue
        img_src = src_m.group("src")
        webp_on_disk = resolve_webp(html_path, img_src)
        if webp_on_disk is None:
            out_parts.append(img_tag)
            last_end = end
            continue
        # Compute webp URL: replace extension in the original URL (preserving query string)
        parsed = urlparse(img_src)
        webp_url = re.sub(r'\.(png|jpg|jpeg)(\?|$)', r'.webp\2', img_src, count=1, flags=re.IGNORECASE)
        wrapped = f'<picture><source srcset="{webp_url}" type="image/webp">{img_tag}</picture>'
        out_parts.append(wrapped)
        last_end = end
        count += 1
    out_parts.append(html[last_end:])
    return "".join(out_parts), count


def main():
    total_files = 0
    total_wraps = 0
    files_changed = 0
    for html_path in DOCS.rglob("*.html"):
        total_files += 1
        try:
            html = html_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  ! read failed: {html_path}: {e}")
            continue
        new_html, count = wrap_imgs_in_html(html, html_path)
        if count > 0:
            html_path.write_text(new_html, encoding="utf-8")
            files_changed += 1
            total_wraps += count
    print(f"Scanned: {total_files} html files")
    print(f"Changed: {files_changed} files")
    print(f"Images wrapped: {total_wraps}")


if __name__ == "__main__":
    main()
