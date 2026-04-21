"""Crop all team page portraits to uniform face-centered squares.

For each <img> referenced on /team/:
  1. Detect face using OpenCV Haar cascade
  2. If face found: compute 1:1 crop centered on face (face ~55% of frame)
  3. If no face: fallback to center-top crop (upper 60% of image)
  4. Resize to 400x400 and save as JPG quality 88

Outputs to docs/media/team-portraits/ and site-src/static/media/team-portraits/
with deterministic filenames (slugified from source path), leaving originals
untouched. Also generates WebP siblings for the build's picture wrapper.

The HTML rewrite (run separately) will point <img> tags on /team/ to the new
portraits.
"""
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
SITE_SRC_STATIC = REPO / "site-src" / "static"

OUT_DOCS = DOCS / "media" / "team-portraits"
OUT_SITE_SRC = SITE_SRC_STATIC / "media" / "team-portraits"
OUT_DOCS.mkdir(parents=True, exist_ok=True)
OUT_SITE_SRC.mkdir(parents=True, exist_ok=True)

TARGET = 400  # pixels
FACE_FRAC = 0.55  # face should fill this fraction of the crop vertically

HAAR = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
HAAR_ALT = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")


def slugify(path: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    return s[:80]


def detect_face(img_bgr: np.ndarray) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    for clf in (HAAR, HAAR_ALT):
        faces = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        if len(faces) > 0:
            # Pick the largest face
            faces = sorted(faces, key=lambda r: r[2] * r[3], reverse=True)
            return tuple(faces[0])
    return None


def center_crop_square(img: Image.Image, face: tuple[int, int, int, int] | None) -> Image.Image:
    w, h = img.size
    if face is None:
        # Fallback: center-top crop (face typically in upper area)
        side = min(w, h)
        left = (w - side) // 2
        # Bias crop upward so face isn't cropped off at top
        top = max(0, int(h * 0.1))
        top = min(top, h - side)
        return img.crop((left, top, left + side, top + side))

    fx, fy, fw, fh = face
    # Enlarge the crop so the face occupies FACE_FRAC of the final frame
    face_center_x = fx + fw / 2
    face_center_y = fy + fh / 2
    target_side = fh / FACE_FRAC
    # Use max so the crop is large enough to include some shoulder area
    target_side = max(target_side, fw / FACE_FRAC)
    # Shift face center slightly down from geometric center (faces look best
    # positioned in the upper third of a circle)
    visual_center_y = face_center_y + target_side * 0.05
    half = target_side / 2
    left = int(round(face_center_x - half))
    top = int(round(visual_center_y - half))
    # Clamp to image bounds
    side = int(round(target_side))
    if side > min(w, h):
        side = min(w, h)
        half = side / 2
        left = int(round(face_center_x - half))
        top = int(round(visual_center_y - half))
    left = max(0, min(left, w - side))
    top = max(0, min(top, h - side))
    return img.crop((left, top, left + side, top + side))


def process_image(src_path: Path, out_name: str) -> bool:
    try:
        # Read via OpenCV for face detection
        img_bgr = cv2.imdecode(np.fromfile(str(src_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise RuntimeError("cv2 failed to read")
        face = detect_face(img_bgr)

        with Image.open(src_path) as img:
            img.load()
            if img.mode != "RGB":
                img = img.convert("RGB")
            cropped = center_crop_square(img, face)
            cropped = cropped.resize((TARGET, TARGET), Image.LANCZOS)

        jpg_doc = OUT_DOCS / (out_name + ".jpg")
        jpg_src = OUT_SITE_SRC / (out_name + ".jpg")
        webp_doc = OUT_DOCS / (out_name + ".webp")
        webp_src = OUT_SITE_SRC / (out_name + ".webp")
        cropped.save(jpg_doc, format="JPEG", quality=88, optimize=True, progressive=True)
        shutil.copy2(jpg_doc, jpg_src)
        cropped.save(webp_doc, format="WEBP", quality=85, method=6)
        shutil.copy2(webp_doc, webp_src)
        return face is not None
    except Exception as e:
        print(f"  ! failed: {src_path.name}: {e}")
        return False


def main():
    team_html = (DOCS / "team" / "index.html").read_text(encoding="utf-8", errors="replace")
    srcs = re.findall(r'<img[^>]+src="([^"]+\.(?:png|jpg|jpeg|webp))"', team_html, re.IGNORECASE)
    # Skip logo, background, non-portrait images
    EXCLUDE = (
        "1477332210.png",  # ALIUS logo
        "background-images",
    )
    uniq: list[tuple[str, Path]] = []
    seen_names = set()
    for s in srcs:
        if any(ex in s for ex in EXCLUDE):
            continue
        if s.lstrip("/").startswith("media/images/"):
            local = DOCS / s.lstrip("/")
        else:
            continue
        if not local.exists():
            continue
        name = slugify(s)
        if name in seen_names:
            continue
        seen_names.add(name)
        uniq.append((s, local))

    print(f"Processing {len(uniq)} unique team portraits...")
    face_hits = 0
    for src, path in uniq:
        name = slugify(src)
        ok = process_image(path, name)
        if ok:
            face_hits += 1
    print(f"Face-detected: {face_hits}/{len(uniq)} (fallback center-crop for rest)")
    print(f"Output: {OUT_DOCS}")


if __name__ == "__main__":
    main()
