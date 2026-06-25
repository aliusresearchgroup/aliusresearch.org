#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def project_root_from_manifest(manifest: Path) -> Path:
    return manifest.resolve().parent.parent


def run_step(command: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode, result.stdout


def load_results(project_root: Path) -> list[dict[str, Any]]:
    result_path = project_root / "reports" / "validation" / "validation-results.json"
    return json.loads(result_path.read_text(encoding="utf-8"))


def evaluate_result(result: dict[str, Any], max_changed_ratio: float, max_mean_abs: float) -> dict[str, Any]:
    if result.get("skipped"):
        return {
            "name": result["name"],
            "status": "skipped",
            "reason": result.get("skip_reason", "not marked reconstructed"),
            "worst_pages": [],
        }
    failures = []
    if result.get("reference_pdf") and result.get("page_count_match") is not True:
        failures.append("page-count")
    if result.get("reference_pdf") and result.get("page_size_match") is not True:
        failures.append("page-size")
    if result.get("required_fonts_present") is not True:
        failures.append("required-fonts")
    if result.get("front_matter_match") is not True:
        failures.append("front-matter")

    page_failures = [
        page
        for page in result.get("page_diffs", [])
        if page["changed_ratio"] > max_changed_ratio or page["mean_abs"] > max_mean_abs
    ]
    if page_failures:
        failures.append("visual-diff")

    worst_pages = sorted(
        result.get("page_diffs", []),
        key=lambda page: (page["changed_ratio"], page["mean_abs"]),
        reverse=True,
    )[:5]
    return {
        "name": result["name"],
        "status": "pass" if not failures else "needs-work",
        "failures": failures,
        "worst_pages": worst_pages,
    }


def report_content(
    manifest: Path,
    round_number: int,
    evaluations: list[dict[str, Any]],
    max_changed_ratio: float,
    max_mean_abs: float,
    command_log: list[str],
) -> str:
    active = [item for item in evaluations if item["status"] != "skipped"]
    passed = active and all(item["status"] == "pass" for item in active)
    lines = [
        "# Visual Fidelity Loop",
        "",
        f"- Manifest: `{manifest.as_posix()}`",
        f"- Round: `{round_number}`",
        f"- Max changed ratio: `{max_changed_ratio}`",
        f"- Max mean absolute diff: `{max_mean_abs}`",
        f"- Overall status: `{'pass' if passed else 'needs-work'}`",
        "",
        "## Results",
        "",
    ]
    for evaluation in evaluations:
        lines.append(f"### {evaluation['name']}")
        lines.append("")
        lines.append(f"- Status: `{evaluation['status']}`")
        if evaluation["status"] == "skipped":
            lines.append(f"- Reason: `{evaluation['reason']}`")
            lines.append("")
            continue
        failures = ", ".join(evaluation.get("failures", [])) or "none"
        lines.append(f"- Failed gates: `{failures}`")
        for page in evaluation["worst_pages"]:
            hints = ", ".join(page.get("hints", [])) or "no strong hint"
            lines.append(
                f"- Worst page `{page['page']}`: changed_ratio=`{page['changed_ratio']}`, "
                f"mean_abs=`{page['mean_abs']}`, hints=`{hints}`"
            )
            if page.get("candidate_image"):
                lines.append(f"  Candidate: `{page['candidate_image']}`")
            if page.get("reference_image"):
                lines.append(f"  Reference: `{page['reference_image']}`")
            if page.get("diff_image"):
                lines.append(f"  Diff: `{page['diff_image']}`")
        lines.append("")
    if command_log:
        lines.extend(["## Command Log", ""])
        lines.extend(command_log)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ALIUS Bulletin compile/render/diff loop and write a fidelity report.")
    parser.add_argument("--manifest", type=Path, default=Path("fixtures/fixture-manifest.json"))
    parser.add_argument("--max-rounds", type=int, default=1)
    parser.add_argument("--max-changed-ratio", type=float, default=0.08)
    parser.add_argument("--max-mean-abs", type=float, default=0.04)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--include-incomplete", action="store_true")
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    root = project_root_from_manifest(manifest)
    report_path = root / "reports" / "VISUAL_FIDELITY_LOOP.md"
    command_log: list[str] = []
    final_evaluations: list[dict[str, Any]] = []

    for round_number in range(1, args.max_rounds + 1):
        preflight_cmd = [sys.executable, "scripts/preflight_editorial.py", "--manifest", manifest.as_posix()]
        code, output = run_step(preflight_cmd, root)
        command_log.append(f"- `{' '.join(preflight_cmd)}` -> `{code}`")
        if code != 0:
            command_log.append("```")
            command_log.append(output.strip())
            command_log.append("```")
            break

        validate_cmd = [
            sys.executable,
            "scripts/validate_bulletins.py",
            "--manifest",
            manifest.as_posix(),
            "--dpi",
            str(args.dpi),
            "--save-renders",
        ]
        if args.include_incomplete:
            validate_cmd.append("--include-incomplete")
        code, output = run_step(validate_cmd, root)
        command_log.append(f"- `{' '.join(validate_cmd)}` -> `{code}`")
        if code != 0:
            command_log.append("```")
            command_log.append(output.strip())
            command_log.append("```")
            break

        results = load_results(root)
        final_evaluations = [
            evaluate_result(result, args.max_changed_ratio, args.max_mean_abs)
            for result in results
        ]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            report_content(
                manifest,
                round_number,
                final_evaluations,
                args.max_changed_ratio,
                args.max_mean_abs,
                command_log,
            ),
            encoding="utf-8",
        )
        active = [item for item in final_evaluations if item["status"] != "skipped"]
        if active and all(item["status"] == "pass" for item in active):
            break

    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
