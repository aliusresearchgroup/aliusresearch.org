#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGINAL_ROOT = Path(r"C:\Users\cogpsy-vrlab\Documents\ALIUS Bulletin")
DEFAULT_OUTPUT_ROOT = SOURCE_ROOT / "reports" / "inventory"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_file(path: Path, original_root: Path) -> str:
    rel = path.relative_to(original_root).as_posix()
    lower = rel.lower()
    suffix = path.suffix.lower()
    if "(zip001)" in lower:
        return "duplicate-copy"
    if "/previous versions/" in lower:
        return "previous-version"
    if lower.startswith("guidelines/"):
        return "guideline-source"
    if lower.startswith("alius open call/"):
        return "open-call-or-literature"
    if lower.startswith("podcast/"):
        return "podcast-source"
    if suffix in {".mp3", ".mp4", ".m4a", ".wav", ".mkv", ".vtt", ".aup", ".au"}:
        return "audio-video-or-transcript"
    if lower.startswith("alius bulletin #4") and suffix == ".html":
        return "issue-04-html-source"
    if any(lower.startswith(f"alius bulletin #{issue}/") for issue in (5, 6, 7)):
        if suffix == ".pdf":
            return "original-render-or-reference-pdf"
        if suffix in {".doc", ".docx", ".html", ".svg"}:
            return "bulletin-source-candidate"
    if suffix in {".doc", ".docx", ".pdf", ".html", ".svg"}:
        return "supporting-document"
    return "non-document-asset"


def issue_registry_summary(issue_index: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    reconstructed: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for issue in issue_index.get("issues", []):
        for piece in issue.get("pieces", []):
            item = {
                "issue": issue["name"],
                "slug": piece["slug"],
                "title": piece["title"],
                "status": piece.get("status", "unknown"),
                "reference_pdf": piece.get("reference_pdf", ""),
                "source_page": piece.get("source_page", ""),
            }
            if piece.get("status") == "reconstructed":
                reconstructed.append(item)
            else:
                missing.append(item)
    return reconstructed, missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit original ALIUS Bulletin inventory against the Overleaf registry.")
    parser.add_argument("--original-root", type=Path, default=DEFAULT_ORIGINAL_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    original_root = args.original_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in original_root.rglob("*") if path.is_file())
    issue_index = read_json(SOURCE_ROOT / "content" / "issues" / "issue-index.json")
    reconstructed, missing = issue_registry_summary(issue_index)

    rows = []
    for path in files:
        rows.append(
            {
                "relative_path": path.relative_to(original_root).as_posix(),
                "extension": path.suffix.lower() or "(none)",
                "size_bytes": path.stat().st_size,
                "classification": classify_file(path, original_root),
            }
        )

    extension_counts = Counter(row["extension"] for row in rows)
    classification_counts = Counter(row["classification"] for row in rows)

    result = {
        "original_root": str(original_root),
        "total_files": len(rows),
        "extension_counts": dict(extension_counts.most_common()),
        "classification_counts": dict(classification_counts.most_common()),
        "reconstructed_registry_entries": reconstructed,
        "missing_registry_entries": missing,
        "files": rows,
    }
    (output_root / "source-inventory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# ALIUS Bulletin Source Inventory",
        "",
        f"- Original root: `{original_root}`",
        f"- Total files: `{len(rows)}`",
        f"- Reconstructed registry entries: `{len(reconstructed)}`",
        f"- Indexed but not reconstructed entries: `{len(missing)}`",
        "",
        "## Extension Counts",
        "",
    ]
    for extension, count in extension_counts.most_common():
        lines.append(f"- `{extension}`: `{count}`")
    lines.extend(["", "## Classification Counts", ""])
    for classification, count in classification_counts.most_common():
        lines.append(f"- `{classification}`: `{count}`")
    lines.extend(["", "## Reconstructed In Overleaf", ""])
    for item in reconstructed:
        lines.append(f"- `{item['issue']}/{item['slug']}` - {item['title']}")
    lines.extend(["", "## Still Missing From Overleaf", ""])
    for item in missing:
        lines.append(f"- `{item['issue']}/{item['slug']}` - {item['title']} (`{item['status']}`)")
    lines.extend(["", "## Document-Like Original Files", ""])
    for row in rows:
        if row["extension"] in {".doc", ".docx", ".pdf", ".html", ".svg"}:
            lines.append(f"- `{row['classification']}` - `{row['relative_path']}`")
    (output_root / "SOURCE_INVENTORY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {output_root}")


if __name__ == "__main__":
    main()
