#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from docx import Document
from ftfy import fix_text


GREEN_HEX = {"1F8135", "008000", "00B050"}
SECTION_HEADINGS = {"abstract", "references", "acknowledgments"}


@dataclass
class ChunkStyle:
    color: str | None
    size: float | None
    bold: bool
    italic: bool


@dataclass
class Chunk:
    text: str
    style: ChunkStyle


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for char in text:
        out.append(replacements.get(char, char))
    return "".join(out)


def normalize_space(text: str) -> str:
    text = fix_text(text)
    text = text.replace("\u200b", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_run_text(text: str) -> list[str]:
    parts = []
    for chunk in text.replace("\r", "").split("\n"):
        parts.append(chunk)
    return parts


def flatten_chunks(doc: Document) -> list[Chunk]:
    chunks: list[Chunk] = []
    for para in doc.paragraphs:
        current_text: list[str] = []
        current_style: ChunkStyle | None = None
        runs = para.runs or []
        if not runs and para.text:
            chunks.append(Chunk(normalize_space(para.text), ChunkStyle(None, None, False, False)))
            continue
        for run in runs:
            color = None
            if run.font.color is not None and run.font.color.rgb is not None:
                color = str(run.font.color.rgb).upper()
            size = float(run.font.size.pt) if run.font.size is not None else None
            style = ChunkStyle(color=color, size=size, bold=bool(run.bold), italic=bool(run.italic))
            parts = split_run_text(run.text)
            for idx, part in enumerate(parts):
                if part:
                    if current_style is None:
                        current_style = style
                    current_text.append(part)
                if idx != len(parts) - 1:
                    text = normalize_space("".join(current_text))
                    if text:
                        chunks.append(Chunk(text, current_style or style))
                    current_text = []
                    current_style = None
        tail = normalize_space("".join(current_text))
        if tail:
            chunks.append(Chunk(tail, current_style or ChunkStyle(None, None, False, False)))
    return [chunk for chunk in chunks if chunk.text]


def first_nonempty(values: Iterable[str]) -> str:
    for value in values:
        if normalize_space(value):
            return normalize_space(value)
    return ""


def extract_abstract_and_keywords(chunks: list[Chunk]) -> tuple[str, str, int]:
    abstract = ""
    keywords = ""
    start_index = 0
    for index, chunk in enumerate(chunks):
        text = chunk.text.lower()
        if text == "abstract":
            start_index = index + 1
            break
    if start_index:
        collected = []
        for index in range(start_index, len(chunks)):
            text = chunks[index].text
            if re.match(r"^(keywords?|key words)\s*:", text, flags=re.IGNORECASE):
                keywords = re.sub(r"^(keywords?|key words)\s*:\s*", "", text, flags=re.IGNORECASE)
                return normalize_space(" ".join(collected)), normalize_space(keywords), index + 1
            collected.append(text)
        abstract = normalize_space(" ".join(collected))
    return normalize_space(abstract), normalize_space(keywords), start_index


def is_section_heading(text: str) -> bool:
    return normalize_space(text).lower() in SECTION_HEADINGS


def is_pull_quote(chunk: Chunk) -> bool:
    size = chunk.style.size or 0.0
    if size < 14.8:
        return False
    text = normalize_space(chunk.text)
    if len(text) > 260:
        return False
    if text.lower() in SECTION_HEADINGS:
        return False
    return True


def is_question(chunk: Chunk) -> bool:
    color = (chunk.style.color or "").upper()
    text = normalize_space(chunk.text)
    if color in GREEN_HEX:
        return True
    size = chunk.style.size or 0.0
    if size and size <= 13.2 and text.endswith("?"):
        return True
    if chunk.style.bold and color in GREEN_HEX:
        return True
    return False


def split_speaker(text: str) -> tuple[str | None, str]:
    match = re.match(
        r"^(((?:[A-Z]\.){1,3}\s+[A-Z][A-Za-z'’.-]+)|(?:[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){0,2})):\s+(.+)$",
        text,
    )
    if not match:
        return None, text
    return match.group(1).strip() + ":", match.group(3).strip()


def coalesce_items(items: list[dict]) -> list[dict]:
    coalesced: list[dict] = []
    for item in items:
        if (
            coalesced
            and item["kind"] == "pullquote"
            and coalesced[-1]["kind"] == "pullquote"
        ):
            coalesced[-1]["text"] += r"\\" + item["text"]
            continue
        coalesced.append(item)
    return coalesced


def classify_body(chunks: list[Chunk], piece_type: str, start_index: int) -> list[dict]:
    items: list[dict] = []
    in_references = False
    for chunk in chunks[start_index:]:
        text = normalize_space(chunk.text)
        if not text:
            continue
        lowered = text.lower()
        if lowered == "abstract":
            continue
        if re.match(r"^(keywords?|key words)\s*:", text, flags=re.IGNORECASE):
            continue
        if is_section_heading(text):
            items.append({"kind": "section_heading", "text": text})
            in_references = lowered == "references"
            continue
        if in_references:
            items.append({"kind": "reference", "text": text})
            continue
        if is_pull_quote(chunk):
            items.append({"kind": "pullquote", "text": text})
            continue
        speaker, speaker_text = split_speaker(text)
        if speaker and piece_type in {"interview", "conversation"}:
            items.append({"kind": "speaker_answer", "speaker": speaker, "text": speaker_text})
            continue
        if piece_type in {"interview", "conversation"} and is_question(chunk):
            items.append({"kind": "question", "text": text})
            continue
        items.append({"kind": "paragraph", "text": text})
    return items


def write_body_tex(items: list[dict], output_path: Path) -> None:
    lines = []
    for item in items:
        kind = item["kind"]
        if kind == "question":
            lines.append(r"\AliusQuestion{" + tex_escape(item["text"]) + "}")
        elif kind == "speaker_answer":
            lines.append(
                r"\AliusSpeakerAnswer{" + tex_escape(item["speaker"]) + "}{" + tex_escape(item["text"]) + "}"
            )
        elif kind == "pullquote":
            lines.append(r"\AliusPullQuote{" + tex_escape(item["text"]) + "}")
        elif kind == "section_heading":
            lines.append(r"\AliusSectionHeading{" + tex_escape(item["text"]) + "}")
        elif kind == "reference":
            lines.append(r"\AliusReferenceEntry{" + tex_escape(item["text"]) + "}")
        else:
            lines.append(r"\AliusParagraph{" + tex_escape(item["text"]) + "}")
        lines.append("")
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def decode_cli_markup(text: str) -> str:
    repaired = fix_text(text)
    return repaired.replace("[[BR]]", r"\\").replace("[[NBSP]]", "~")


def contributor_arg_to_json(raw: str) -> dict:
    name, details = raw.split("::", 1)
    return {
        "name": fix_text(name.strip()),
        "details": [fix_text(part.strip()) for part in details.split("|") if part.strip()],
    }


def contributor_tex(details: list[str]) -> str:
    return r"\\".join(tex_escape(part) for part in details)


def write_meta_tex(metadata: dict, output_path: Path) -> None:
    lines = [
        r"\AliusSetIssueNumber{" + tex_escape(str(metadata["issue_number"])) + "}",
        r"\AliusSetYear{" + tex_escape(str(metadata["year"])) + "}",
        r"\AliusSetPieceSlug{" + tex_escape(metadata["slug"]) + "}",
        r"\AliusSetPieceType{" + tex_escape(metadata["piece_type"]) + "}",
        r"\AliusSetTitle{" + metadata["title_tex"] + "}",
    ]
    if metadata.get("subtitle_tex"):
        lines.append(r"\AliusSetSubtitle{" + metadata["subtitle_tex"] + "}")
    if metadata.get("credit_line_tex"):
        lines.append(r"\AliusSetCreditLine{" + metadata["credit_line_tex"] + "}")
    if metadata.get("running_title"):
        lines.append(r"\AliusSetRunningTitle{" + tex_escape(metadata["running_title"]) + "}")
    lines.append(r"\AliusSetCitationLabel{" + tex_escape(metadata["citation_label"]) + "}")
    lines.append(r"\AliusSetStandaloneCitation{" + metadata["standalone_citation_tex"] + "}")
    if metadata.get("bundle_citation_tex"):
        lines.append(r"\AliusSetBundleCitation{" + metadata["bundle_citation_tex"] + "}")
    lines.append(r"\AliusSetAbstract{" + tex_escape(metadata["abstract"]) + "}")
    lines.append(r"\AliusSetKeywordsLabel{" + tex_escape(metadata["keywords_label"]) + "}")
    lines.append(r"\AliusSetKeywords{" + tex_escape(metadata["keywords"]) + "}")
    if metadata.get("title_size"):
        lines.append(r"\AliusSetTitleSize{" + str(metadata["title_size"][0]) + "}{" + str(metadata["title_size"][1]) + "}")
    if metadata.get("subtitle_size"):
        lines.append(
            r"\AliusSetSubtitleSize{" + str(metadata["subtitle_size"][0]) + "}{" + str(metadata["subtitle_size"][1]) + "}"
        )
    if metadata.get("credit_size"):
        lines.append(r"\AliusSetCreditSize{" + str(metadata["credit_size"][0]) + "}{" + str(metadata["credit_size"][1]) + "}")
    lines.append(r"\AliusClearContributors")
    for contributor in metadata["contributors"]:
        lines.append(
            r"\AliusAddContributor{" + tex_escape(contributor["name"]) + "}{" + contributor_tex(contributor["details"]) + "}"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_fixture_tex(project_root: Path, slug: str, output_path: Path) -> None:
    rel_class = Path("../../aliusbulletin.cls")
    rel_meta = Path("../../content/pieces") / slug / "meta.tex"
    rel_body = Path("../../content/pieces") / slug / "body.tex"
    content = "\n".join(
        [
            r"\documentclass{" + rel_class.as_posix().replace(".cls", "") + "}",
            r"\input{" + rel_meta.as_posix() + "}",
            r"\begin{document}",
            r"\AliusStartPiece",
            r"\input{" + rel_body.as_posix() + "}",
            r"\AliusFinishPiece",
            r"\end{document}",
            "",
        ]
    )
    output_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract an ALIUS Bulletin DOCX into piece JSON and TeX.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--piece-type", required=True, choices=["interview", "conversation", "podcast", "commentary", "review", "editorial-note"])
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--year", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--credit-line", default="")
    parser.add_argument("--running-title", default="")
    parser.add_argument("--citation-label", default="Cite as:")
    parser.add_argument("--standalone-citation", required=True)
    parser.add_argument("--bundle-citation", default="")
    parser.add_argument("--keywords-label", default="Keywords:")
    parser.add_argument("--contributor", action="append", default=[])
    parser.add_argument("--title-size", nargs=2, type=int)
    parser.add_argument("--subtitle-size", nargs=2, type=int)
    parser.add_argument("--credit-size", nargs=2, type=int)
    args = parser.parse_args()

    doc = Document(str(args.source))
    chunks = flatten_chunks(doc)
    abstract, keywords, start_index = extract_abstract_and_keywords(chunks)
    items = coalesce_items(classify_body(chunks, args.piece_type, start_index))

    content_dir = args.project_root / "content" / "pieces" / args.slug
    fixture_dir = args.project_root / "fixtures" / "pieces"
    content_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "slug": args.slug,
        "piece_type": args.piece_type,
        "issue_number": args.issue_number,
        "year": args.year,
        "title": decode_cli_markup(args.title),
        "subtitle": decode_cli_markup(args.subtitle),
        "credit_line": decode_cli_markup(args.credit_line),
        "running_title": decode_cli_markup(args.running_title),
        "citation_label": args.citation_label,
        "standalone_citation": decode_cli_markup(args.standalone_citation),
        "bundle_citation": decode_cli_markup(args.bundle_citation),
        "keywords_label": args.keywords_label,
        "abstract": abstract,
        "keywords": keywords,
        "contributors": [contributor_arg_to_json(raw) for raw in args.contributor],
        "title_tex": decode_cli_markup(args.title),
        "subtitle_tex": decode_cli_markup(args.subtitle),
        "credit_line_tex": decode_cli_markup(args.credit_line),
        "standalone_citation_tex": tex_escape(decode_cli_markup(args.standalone_citation)),
        "bundle_citation_tex": tex_escape(decode_cli_markup(args.bundle_citation)) if args.bundle_citation else "",
        "title_size": args.title_size,
        "subtitle_size": args.subtitle_size,
        "credit_size": args.credit_size,
        "source_docx": str(args.source),
        "body_items": items,
    }

    write_body_tex(items, content_dir / "body.tex")
    write_meta_tex(metadata, content_dir / "meta.tex")
    (content_dir / "piece.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_fixture_tex(args.project_root, args.slug, fixture_dir / f"{args.slug}.tex")


if __name__ == "__main__":
    main()
