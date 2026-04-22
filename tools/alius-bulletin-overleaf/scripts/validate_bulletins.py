#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_fixture(project_root: Path, main_tex: Path, slug: str) -> Path:
    build_dir = project_root / "build" / slug
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "latexmk",
            "-lualatex",
            f"-outdir={build_dir.as_posix()}",
            f"-auxdir={build_dir.as_posix()}",
            main_tex.as_posix(),
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"latexmk failed for {slug}\n{result.stdout}")
    return build_dir / (main_tex.stem + ".pdf")


def pdf_page_sizes(path: Path) -> list[tuple[float, float]]:
    doc = fitz.open(path)
    return [(round(page.rect.width, 2), round(page.rect.height, 2)) for page in doc]


def page_sizes_match(candidate_sizes: list[tuple[float, float]], reference_sizes: list[tuple[float, float]], tolerance: float = 1.0) -> bool:
    if not candidate_sizes or not reference_sizes:
        return False
    for (cand_w, cand_h), (ref_w, ref_h) in zip(candidate_sizes, reference_sizes):
        if abs(cand_w - ref_w) > tolerance or abs(cand_h - ref_h) > tolerance:
            return False
    return True


def pdf_fonts(path: Path) -> list[str]:
    result = subprocess.run(
        ["pdffonts", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    fonts = []
    for line in result.stdout.splitlines()[2:]:
        parts = line.split()
        if parts:
            fonts.append(parts[0])
    return fonts


def render_page(pdf_path: Path, page_index: int, dpi: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return image


def diff_images(reference: Image.Image, candidate: Image.Image) -> tuple[float, float, Image.Image]:
    if reference.size != candidate.size:
        target = (min(reference.width, candidate.width), min(reference.height, candidate.height))
        reference = reference.resize(target)
        candidate = candidate.resize(target)
    ref_arr = np.asarray(reference, dtype=np.int16)
    cand_arr = np.asarray(candidate, dtype=np.int16)
    diff = np.abs(ref_arr - cand_arr)
    mean_abs = float(diff.mean() / 255.0)
    changed_ratio = float((diff.max(axis=2) > 16).mean())
    diff_heat = np.zeros_like(ref_arr, dtype=np.uint8)
    diff_heat[..., 0] = np.clip(diff.max(axis=2) * 4, 0, 255).astype(np.uint8)
    diff_heat[..., 1] = np.clip(ref_arr.mean(axis=2), 0, 255).astype(np.uint8)
    diff_image = Image.fromarray(diff_heat, mode="RGB")
    return mean_abs, changed_ratio, diff_image


def first_page_text(path: Path) -> str:
    doc = fitz.open(path)
    return " ".join(doc[0].get_text("text").split())


def normalize_text_for_compare(text: str) -> str:
    normalized = text.replace("\\\\", " ")
    normalized = re.sub(r"\\[A-Za-z@]+(?:\{[^}]*\})*", " ", normalized)
    normalized = re.sub(r"[{}]", " ", normalized)
    normalized = " ".join(normalized.split())
    return normalized.strip()


def expected_strings(project_root: Path, fixture: dict) -> list[str]:
    if not fixture.get("content_dir"):
        return []
    piece_json = project_root / fixture["content_dir"] / "piece.json"
    data = json.loads(piece_json.read_text(encoding="utf-8"))
    values = [data.get("title", ""), data.get("subtitle", ""), data.get("credit_line", "")]
    values.extend(contributor["name"] for contributor in data.get("contributors", []))
    return [normalize_text_for_compare(value) for value in values if value]


def region_hints(diff_image: Image.Image) -> list[str]:
    arr = np.asarray(diff_image)
    intensity = arr[..., 0].astype(np.float32)
    height = intensity.shape[0]
    top = intensity[: math.floor(height * 0.22)].mean()
    middle = intensity[math.floor(height * 0.22) : math.floor(height * 0.82)].mean()
    bottom = intensity[math.floor(height * 0.82) :].mean()
    hints = []
    if top > middle * 1.1:
        hints.append("title/header/front-matter")
    if bottom > middle * 1.1:
        hints.append("footer/page-bottom")
    if middle > top * 1.05 and middle > bottom * 1.05:
        hints.append("body-layout/pull-quotes")
    return hints


def validate_fixture(project_root: Path, repo_root: Path, fixture: dict, report_root: Path) -> dict:
    slug = fixture["name"]
    main_tex = project_root / fixture["main_tex"]
    candidate_pdf = compile_fixture(project_root, main_tex, slug)
    reference_pdf = repo_root / fixture["reference_pdf"] if fixture.get("reference_pdf") else None

    result = {
        "name": slug,
        "candidate_pdf": str(candidate_pdf),
        "reference_pdf": str(reference_pdf) if reference_pdf else None,
        "page_count_match": None,
        "page_size_match": None,
        "required_fonts_present": True,
        "front_matter_match": True,
        "page_diffs": [],
    }

    if not reference_pdf or not reference_pdf.exists():
        return result

    candidate_sizes = pdf_page_sizes(candidate_pdf)
    reference_sizes = pdf_page_sizes(reference_pdf)
    result["page_count_match"] = len(candidate_sizes) == len(reference_sizes)
    result["page_size_match"] = page_sizes_match(candidate_sizes, reference_sizes)
    result["candidate_first_page_size"] = candidate_sizes[0] if candidate_sizes else None
    result["reference_first_page_size"] = reference_sizes[0] if reference_sizes else None

    fonts = pdf_fonts(candidate_pdf)
    required_fonts = fixture.get("required_fonts", [])
    result["required_fonts_present"] = all(any(required in font for font in fonts) for required in required_fonts)

    page_text = normalize_text_for_compare(first_page_text(candidate_pdf))
    for expected in expected_strings(project_root, fixture):
        if expected and expected not in page_text:
            result["front_matter_match"] = False
            break

    report_dir = report_root / slug
    report_dir.mkdir(parents=True, exist_ok=True)

    for page_index in range(min(len(candidate_sizes), len(reference_sizes))):
        ref_image = render_page(reference_pdf, page_index, dpi=160)
        cand_image = render_page(candidate_pdf, page_index, dpi=160)
        mean_abs, changed_ratio, diff_image = diff_images(ref_image, cand_image)
        diff_path = report_dir / f"page-{page_index + 1:03d}.diff.png"
        diff_image.save(diff_path)
        result["page_diffs"].append(
            {
                "page": page_index + 1,
                "mean_abs": round(mean_abs, 5),
                "changed_ratio": round(changed_ratio, 5),
                "hints": region_hints(diff_image),
                "diff_image": str(diff_path),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile and validate ALIUS bulletin fixtures against reference PDFs.")
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    project_root = manifest_path.parent.parent
    repo_root = project_root.parent.parent
    report_root = project_root / "reports" / "validation"
    report_root.mkdir(parents=True, exist_ok=True)

    summary_lines = ["# Validation Report", ""]
    all_results = []
    for section in ("pieces", "issues"):
        for fixture in manifest.get(section, []):
            result = validate_fixture(project_root, repo_root, fixture, report_root)
            all_results.append(result)
            summary_lines.append(f"## {result['name']}")
            summary_lines.append("")
            summary_lines.append(f"- Candidate PDF: `{result['candidate_pdf']}`")
            if result["reference_pdf"]:
                summary_lines.append(f"- Reference PDF: `{result['reference_pdf']}`")
                summary_lines.append(f"- Page count match: `{result['page_count_match']}`")
                summary_lines.append(f"- Page size match: `{result['page_size_match']}`")
                summary_lines.append(f"- Candidate first-page size: `{result['candidate_first_page_size']}`")
                summary_lines.append(f"- Reference first-page size: `{result['reference_first_page_size']}`")
                summary_lines.append(f"- Required fonts present: `{result['required_fonts_present']}`")
                summary_lines.append(f"- Front matter match: `{result['front_matter_match']}`")
                worst = sorted(result["page_diffs"], key=lambda item: item["changed_ratio"], reverse=True)[:5]
                for page in worst:
                    hints = ", ".join(page["hints"]) if page["hints"] else "no strong hint"
                    summary_lines.append(
                        f"- Worst page `{page['page']}`: changed_ratio=`{page['changed_ratio']}`, mean_abs=`{page['mean_abs']}`, hints=`{hints}`"
                    )
            else:
                summary_lines.append("- Reference PDF: `not configured`")
            summary_lines.append("")
    (report_root / "VALIDATION_REPORT.md").write_text("\n".join(summary_lines), encoding="utf-8")
    (report_root / "validation-results.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
