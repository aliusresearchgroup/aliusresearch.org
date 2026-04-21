"""Minify CSS and JS assets in-place. Originals archived first.

Targets only unminified, non-vendor-runtime files. Skips already-minified files
and files whose minification risks runtime breakage.
"""
import os
import shutil
import sys
from pathlib import Path

import csscompressor
import jsmin

REPO = Path(__file__).resolve().parents[2]
SITE_SRC = REPO / "site-src" / "static"
DOCS = REPO / "docs"
ARCHIVE = REPO / "archive" / "css-js-unminified"
ARCHIVE.mkdir(parents=True, exist_ok=True)

CSS_FILES = [
    "assets/vendor/weebly-site/files/main_style.css",
    "assets/vendor/editmysite/cdn11.editmysite.com/css/social-icons.css",
    "assets/vendor/editmysite/cdn11.editmysite.com/css/old/fancybox.css",
    "assets/vendor/editmysite/cdn11.editmysite.com/css/old/slideshow/slideshow.css",
]

JS_FILES = [
    "assets/vendor/weebly-site/files/theme/files/custom.js",
    "assets/vendor/weebly-site/files/theme/files/mobile.js",
    "assets/vendor/weebly-site/files/theme/files/plugins.js",
    "assets/vendor/editmysite/cdn11.editmysite.com/js/site/main.js",
    "assets/vendor/editmysite/cdn11.editmysite.com/js/old/slideshow-jq.js",
]


def archive_original(src_path: Path, rel_path: str):
    dest = ARCHIVE / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src_path, dest)


def minify_css(rel_path: str):
    src_path = SITE_SRC / rel_path
    if not src_path.exists():
        print(f"SKIP (missing): {rel_path}")
        return
    original = src_path.read_text(encoding="utf-8", errors="replace")
    original_size = len(original.encode("utf-8"))
    # Skip if already minified (heuristic: single line + ratio)
    line_count = original.count("\n")
    if line_count < 5 and original_size > 1000:
        print(f"SKIP (already minified): {rel_path} [{original_size} bytes, {line_count} lines]")
        return
    archive_original(src_path, rel_path)
    minified = csscompressor.compress(original)
    src_path.write_text(minified, encoding="utf-8")
    # Mirror to docs/
    docs_path = DOCS / rel_path
    if docs_path.exists():
        docs_path.write_text(minified, encoding="utf-8")
    new_size = len(minified.encode("utf-8"))
    savings_pct = 100 * (1 - new_size / original_size) if original_size else 0
    print(f"CSS : {rel_path}: {original_size:>9,} -> {new_size:>9,} bytes ({savings_pct:4.1f}% saved)")


def minify_js(rel_path: str):
    src_path = SITE_SRC / rel_path
    if not src_path.exists():
        print(f"SKIP (missing): {rel_path}")
        return
    original = src_path.read_text(encoding="utf-8", errors="replace")
    original_size = len(original.encode("utf-8"))
    line_count = original.count("\n")
    if line_count < 5 and original_size > 1000:
        print(f"SKIP (already minified): {rel_path} [{original_size} bytes, {line_count} lines]")
        return
    archive_original(src_path, rel_path)
    minified = jsmin.jsmin(original)
    src_path.write_text(minified, encoding="utf-8")
    docs_path = DOCS / rel_path
    if docs_path.exists():
        docs_path.write_text(minified, encoding="utf-8")
    new_size = len(minified.encode("utf-8"))
    savings_pct = 100 * (1 - new_size / original_size) if original_size else 0
    print(f"JS  : {rel_path}: {original_size:>9,} -> {new_size:>9,} bytes ({savings_pct:4.1f}% saved)")


def main():
    print("=" * 70)
    print("CSS Minification")
    print("=" * 70)
    for f in CSS_FILES:
        minify_css(f)
    print()
    print("=" * 70)
    print("JS Minification")
    print("=" * 70)
    for f in JS_FILES:
        minify_js(f)
    print()
    print(f"Originals archived to: {ARCHIVE}")


if __name__ == "__main__":
    main()
