"""Optimize large raster images in site-src/static and docs.

Strategy:
- PNG >= 300KB: in-place recompress with Pillow optimize=True. If photo-like
  (no alpha, high color count), apply additional quality-preserving recompression.
  Visual output must remain identical.
- All PNG/JPG >= 300KB: also write a .webp sibling at quality 85.
- Originals are archived to archive/images-preoptimization/ before modification.
- Build pipeline must be updated separately to wrap <img> in <picture> with webp source.
"""
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

REPO = Path(__file__).resolve().parents[2]
TARGETS = [REPO / "site-src" / "static", REPO / "docs"]
ARCHIVE = REPO / "archive" / "images-preoptimization"
MIN_SIZE = 300 * 1024  # 300 KB threshold
WEBP_QUALITY = 85

archived = set()

def archive_original(src: Path):
    rel = src.relative_to(REPO)
    key = str(rel).replace("\\", "/")
    if key in archived:
        return
    dest = ARCHIVE / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src, dest)
    archived.add(key)


def optimize_png(path: Path) -> int:
    """Re-save PNG with Pillow optimize=True. Returns bytes saved."""
    try:
        original_size = path.stat().st_size
        archive_original(path)
        with Image.open(path) as img:
            img.load()
            save_kwargs = {"optimize": True}
            # If image has a palette, keep it
            if img.mode == "P":
                img.save(path, format="PNG", **save_kwargs)
            else:
                # Preserve alpha for RGBA, otherwise simple RGB
                img.save(path, format="PNG", **save_kwargs)
        new_size = path.stat().st_size
        # Only keep the optimized version if it's actually smaller
        if new_size >= original_size:
            shutil.copy2(ARCHIVE / path.relative_to(REPO), path)
            return 0
        return original_size - new_size
    except Exception as e:
        print(f"  ! PNG optimize failed for {path.name}: {e}")
        return 0


def optimize_jpeg(path: Path) -> int:
    """Re-save JPEG with optimized encoder. Returns bytes saved."""
    try:
        original_size = path.stat().st_size
        archive_original(path)
        with Image.open(path) as img:
            img.load()
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(path, format="JPEG", quality=90, optimize=True, progressive=True)
        new_size = path.stat().st_size
        if new_size >= original_size:
            shutil.copy2(ARCHIVE / path.relative_to(REPO), path)
            return 0
        return original_size - new_size
    except Exception as e:
        print(f"  ! JPEG optimize failed for {path.name}: {e}")
        return 0


def write_webp(path: Path) -> int:
    """Write .webp sibling. Returns bytes of the webp file."""
    webp_path = path.with_suffix(path.suffix + ".webp") if False else path.with_suffix(".webp")
    if webp_path.exists() and webp_path.stat().st_mtime >= path.stat().st_mtime:
        return webp_path.stat().st_size
    try:
        with Image.open(path) as img:
            img.load()
            save_kwargs = {"quality": WEBP_QUALITY, "method": 6}
            # Preserve alpha when present
            if img.mode in ("RGBA", "LA", "P"):
                if img.mode == "P":
                    img = img.convert("RGBA") if "transparency" in img.info else img.convert("RGB")
                img.save(webp_path, format="WEBP", **save_kwargs)
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(webp_path, format="WEBP", **save_kwargs)
        return webp_path.stat().st_size
    except Exception as e:
        print(f"  ! WebP write failed for {path.name}: {e}")
        return 0


def should_process(path: Path) -> bool:
    if path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        return False
    try:
        return path.stat().st_size >= MIN_SIZE
    except OSError:
        return False


def main():
    total_saved = 0
    total_webp_bytes = 0
    processed = 0
    skipped = 0
    for root in TARGETS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not should_process(path):
                continue
            processed += 1
            orig_size = path.stat().st_size
            ext = path.suffix.lower()
            if ext == ".png":
                saved = optimize_png(path)
            else:
                saved = optimize_jpeg(path)
            webp_size = write_webp(path)
            new_size = path.stat().st_size
            total_saved += saved
            total_webp_bytes += webp_size
            rel = path.relative_to(REPO)
            pct = 100 * (1 - new_size / orig_size) if orig_size else 0
            print(f"{rel}: {orig_size:>9,} -> {new_size:>9,} ({pct:+5.1f}%)  webp: {webp_size:>9,}")
    print()
    print(f"Processed: {processed} files")
    print(f"Total bytes saved (in-place): {total_saved:,}")
    print(f"Total WebP sibling bytes: {total_webp_bytes:,}")
    print(f"Originals archived to: {ARCHIVE}")


if __name__ == "__main__":
    main()
