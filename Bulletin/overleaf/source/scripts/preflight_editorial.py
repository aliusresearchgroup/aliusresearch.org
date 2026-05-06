#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def british_spellings(text: str) -> list[str]:
    suspects = [
        r"\bprogramme\b",
        r"\brealised\b",
        r"\bbehaviour\b",
        r"\borganisation\b",
        r"\bcolour\b",
    ]
    hits = []
    for pattern in suspects:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            hits.append(match.group(0))
    return hits


def spacing_violations(text: str) -> list[str]:
    patterns = [
        (r"\s+[;:,.!?]", "space-before-punctuation"),
        (r"\bi\.e\.(?!,)", "i.e.-missing-comma"),
        (r"\be\.g\.(?!,)", "e.g.-missing-comma"),
        (r"\s[–-]\s", "spaced-dash"),
    ]
    hits = []
    for pattern, label in patterns:
        if re.search(pattern, text):
            hits.append(label)
    return hits


def summarize_piece(piece_json: Path) -> dict:
    data = json.loads(piece_json.read_text(encoding="utf-8"))
    body_text = "\n".join(item.get("text", "") for item in data.get("body_items", []))
    abstract_words = len(re.findall(r"\b\w+\b", data.get("abstract", "")))
    keywords = [keyword.strip() for keyword in data.get("keywords", "").split(",") if keyword.strip()]
    pullquotes = [item for item in data.get("body_items", []) if item.get("kind") == "pullquote"]
    has_references = any(item.get("kind") == "reference" for item in data.get("body_items", []))
    findings = []
    if abstract_words > 200:
        findings.append(f"abstract-too-long ({abstract_words} words)")
    if data.get("piece_type") in {"interview", "conversation"} and not (2 <= len(pullquotes) <= 6):
        findings.append(f"pullquote-count-out-of-guideline ({len(pullquotes)})")
    if len(keywords) > 5:
        findings.append(f"keyword-count-high ({len(keywords)})")
    if not has_references:
        findings.append("missing-references-section")
    findings.extend(f"british-spelling:{hit}" for hit in british_spellings(body_text + "\n" + data.get("abstract", "")))
    findings.extend(spacing_violations(body_text + "\n" + data.get("abstract", "")))
    return {
        "slug": data["slug"],
        "piece_type": data["piece_type"],
        "abstract_words": abstract_words,
        "keywords": len(keywords),
        "pullquotes": len(pullquotes),
        "has_references": has_references,
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run editorial preflight on ALIUS piece JSON files.")
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    project_root = args.manifest.parent.parent
    report_lines = ["# Editorial Preflight", ""]
    for fixture in manifest.get("pieces", []):
        content_dir = project_root / fixture["content_dir"]
        summary = summarize_piece(content_dir / "piece.json")
        report_lines.append(f"## {summary['slug']}")
        report_lines.append("")
        report_lines.append(f"- Type: `{summary['piece_type']}`")
        report_lines.append(f"- Abstract words: `{summary['abstract_words']}`")
        report_lines.append(f"- Keywords: `{summary['keywords']}`")
        report_lines.append(f"- Pull quotes: `{summary['pullquotes']}`")
        report_lines.append(f"- References present: `{summary['has_references']}`")
        if summary["findings"]:
            for finding in summary["findings"]:
                report_lines.append(f"- Warning: `{finding}`")
        else:
            report_lines.append("- Status: `pass`")
        report_lines.append("")
    report_path = project_root / "reports" / "EDITORIAL_PREFLIGHT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    main()

