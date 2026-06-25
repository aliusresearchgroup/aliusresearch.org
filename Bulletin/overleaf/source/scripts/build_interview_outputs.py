#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image


SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parents[2]
DEFAULT_MANIFEST = SOURCE_ROOT / "fixtures" / "fixture-manifest.json"
DEFAULT_OUTPUT_ROOT = SOURCE_ROOT.parent / "generated-interview-outputs"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_clean_dir(path: Path) -> None:
    allowed_root = SOURCE_ROOT.parent.resolve()
    target = path.resolve()
    if allowed_root != target and allowed_root not in target.parents:
        raise RuntimeError(f"Refusing to write outside {allowed_root}: {target}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def run_latexmk(main_tex: Path, build_dir: Path) -> tuple[int, str, Path]:
    build_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "latexmk",
        "-lualatex",
        "-interaction=nonstopmode",
        f"-outdir={build_dir.as_posix()}",
        f"-auxdir={build_dir.as_posix()}",
        main_tex.as_posix(),
    ]
    result = subprocess.run(
        command,
        cwd=SOURCE_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode, result.stdout, build_dir / f"{main_tex.stem}.pdf"


def pdf_page_count(path: Path) -> int:
    with fitz.open(path) as doc:
        return len(doc)


def pdf_page_sizes(path: Path) -> list[tuple[float, float]]:
    with fitz.open(path) as doc:
        return [(round(page.rect.width, 2), round(page.rect.height, 2)) for page in doc]


def render_page(pdf_path: Path, page_index: int, dpi: int) -> Image.Image:
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


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
    heat = np.zeros_like(ref_arr, dtype=np.uint8)
    intensity = np.clip(diff.max(axis=2) * 4, 0, 255).astype(np.uint8)
    heat[..., 0] = intensity
    heat[..., 1] = np.clip(ref_arr.mean(axis=2), 0, 255).astype(np.uint8)
    heat[..., 2] = np.clip(cand_arr.mean(axis=2), 0, 255).astype(np.uint8)
    return mean_abs, changed_ratio, Image.fromarray(heat, mode="RGB")


def compare_pdf(reference_pdf: Path, candidate_pdf: Path, output_dir: Path, dpi: int, max_pages: int | None) -> dict[str, Any]:
    reference_sizes = pdf_page_sizes(reference_pdf)
    candidate_sizes = pdf_page_sizes(candidate_pdf)
    page_total = min(len(reference_sizes), len(candidate_sizes))
    if max_pages is not None:
        page_total = min(page_total, max_pages)

    pages: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for index in range(page_total):
        reference = render_page(reference_pdf, index, dpi)
        candidate = render_page(candidate_pdf, index, dpi)
        mean_abs, changed_ratio, diff = diff_images(reference, candidate)
        page = index + 1
        reference_path = output_dir / f"page-{page:03d}.reference.png"
        candidate_path = output_dir / f"page-{page:03d}.candidate.png"
        diff_path = output_dir / f"page-{page:03d}.diff.png"
        reference.save(reference_path)
        candidate.save(candidate_path)
        diff.save(diff_path)
        pages.append(
            {
                "page": page,
                "mean_abs": round(mean_abs, 5),
                "changed_ratio": round(changed_ratio, 5),
                "reference_image": str(reference_path),
                "candidate_image": str(candidate_path),
                "diff_image": str(diff_path),
            }
        )

    page_size_match = all(
        abs(reference_sizes[index][0] - candidate_sizes[index][0]) <= 1.0
        and abs(reference_sizes[index][1] - candidate_sizes[index][1]) <= 1.0
        for index in range(page_total)
    )

    return {
        "reference_page_count": len(reference_sizes),
        "candidate_page_count": len(candidate_sizes),
        "page_count_match": len(reference_sizes) == len(candidate_sizes),
        "page_size_match": page_size_match,
        "pages_compared": page_total,
        "page_diffs": pages,
    }


def write_report(results: list[dict[str, Any]], output_root: Path) -> None:
    lines = [
        "# ALIUS Interview Output Report",
        "",
        "Generated from the Overleaf source folder. The PDFs in `pdf/` are newly compiled standalone interview outputs.",
        "",
        "Visual comparisons are rendered into `visual-comparisons/<slug>/` whenever a reference PDF exists.",
        "",
    ]
    for result in results:
        lines.append(f"## {result['name']}")
        lines.append("")
        lines.append(f"- Status: `{result['status']}`")
        if result.get("candidate_pdf"):
            lines.append(f"- Generated PDF: `{result['candidate_pdf']}`")
        if result.get("reference_pdf"):
            lines.append(f"- Reference PDF: `{result['reference_pdf']}`")
        if result.get("compile_log"):
            lines.append(f"- Compile log: `{result['compile_log']}`")
        if result["status"] != "compiled":
            lines.append(f"- Reason: {result.get('reason', 'not available')}")
            lines.append("")
            continue
        comparison = result.get("comparison")
        if comparison:
            lines.append(f"- Page count match: `{comparison['page_count_match']}`")
            lines.append(f"- Candidate page count: `{comparison['candidate_page_count']}`")
            lines.append(f"- Reference page count: `{comparison['reference_page_count']}`")
            lines.append(f"- Page size match: `{comparison['page_size_match']}`")
            lines.append(f"- Pages compared: `{comparison['pages_compared']}`")
            worst = sorted(
                comparison["page_diffs"],
                key=lambda item: (item["changed_ratio"], item["mean_abs"]),
                reverse=True,
            )[:5]
            for page in worst:
                lines.append(
                    f"- Worst page `{page['page']}`: changed_ratio=`{page['changed_ratio']}`, "
                    f"mean_abs=`{page['mean_abs']}`"
                )
        else:
            lines.append("- Reference PDF: `not configured or missing`")
        lines.append("")
    (output_root / "INTERVIEW_OUTPUT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile reconstructed ALIUS interviews into a separate output folder.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dpi", type=int, default=130)
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    manifest = read_json(args.manifest)
    output_root = args.output_root.resolve()
    ensure_clean_dir(output_root)
    pdf_root = output_root / "pdf"
    build_root = output_root / "latex-build"
    comparison_root = output_root / "visual-comparisons"
    log_root = output_root / "logs"
    pdf_root.mkdir(parents=True)
    build_root.mkdir(parents=True)
    log_root.mkdir(parents=True)

    results: list[dict[str, Any]] = []
    for fixture in manifest.get("pieces", []):
        name = fixture["name"]
        if fixture.get("status") != "reconstructed":
            results.append(
                {
                    "name": name,
                    "status": "skipped",
                    "reason": f"fixture status is {fixture.get('status', 'unknown')}",
                }
            )
            continue

        main_tex = SOURCE_ROOT / fixture["main_tex"]
        code, output, build_pdf = run_latexmk(main_tex, build_root / name)
        log_path = log_root / f"{name}.log.txt"
        log_path.write_text(output, encoding="utf-8", errors="replace")
        if code != 0 or not build_pdf.exists():
            results.append(
                {
                    "name": name,
                    "status": "compile-failed",
                    "reason": f"latexmk exit code {code}",
                    "compile_log": str(log_path),
                }
            )
            continue

        candidate_pdf = pdf_root / f"{name}.pdf"
        shutil.copy2(build_pdf, candidate_pdf)
        reference_pdf = REPO_ROOT / fixture["reference_pdf"] if fixture.get("reference_pdf") else None
        result: dict[str, Any] = {
            "name": name,
            "status": "compiled",
            "candidate_pdf": str(candidate_pdf),
            "candidate_page_count": pdf_page_count(candidate_pdf),
            "reference_pdf": str(reference_pdf) if reference_pdf else None,
            "compile_log": str(log_path),
        }
        if reference_pdf and reference_pdf.exists():
            result["comparison"] = compare_pdf(
                reference_pdf,
                candidate_pdf,
                comparison_root / name,
                dpi=args.dpi,
                max_pages=args.max_pages,
            )
        results.append(result)

    (output_root / "interview-output-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_report(results, output_root)
    print(f"Wrote {output_root}")


if __name__ == "__main__":
    main()
