#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image


SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parents[2]
DEFAULT_TARGET_ROOT = REPO_ROOT.parent / "ALIUS-bulletin"
ISSUE_INDEX = SOURCE_ROOT / "content" / "issues" / "issue-index.json"
REFERENCE_DOCS_ROOT = SOURCE_ROOT / "assets" / "reference-docs"
TOP_LEVEL_FOLDERS = ["Interviews", "Shared-assets", "Bulletins", "Instructions", "AI-agents", "Cover-Art"]
INSTRUCTION_BASENAMES = [
    "template_alius_bulletin",
    "editor-checklist",
    "alius-bulletin---guidelines-for-interviews---2022",
    "alius-bulletin---guidelines-for-conversations---2022",
    "alius-bulletin---guidelines-for-podcast---2022",
    "alius-bulletin---guidelines-for-reviews---2022",
    "alius-bulletin---guidelines-for-commentary---2022",
]


FOLDER_NAMES: dict[tuple[str, str], str] = {
    ("1", "carhart-harris"): "Carhart-Harris_Fortier_Milliere",
    ("1", "hohwy"): "Hohwy_Koroma",
    ("1", "luhrmann"): "Luhrmann_Fortier",
    ("1", "mccarthy-jones"): "McCarthy-Jones_Frerejouan",
    ("1", "seligman"): "Seligman_Halloy",
    ("1", "windt"): "Windt_Bucci_Milliere",
    ("2", "friston-biography"): "Friston",
    ("2", "fox"): "Fox_Koroma",
    ("2", "friston"): "Friston_Fortier_Friedman",
    ("2", "metzinger"): "Metzinger_Limanowski_Milliere",
    ("2", "nichols"): "Nichols_Roseman_Timmermann",
    ("2", "oregan"): "ORegan_Erickson-Davis",
    ("2", "ratcliffe"): "Ratcliffe_Frerejouan",
    ("2", "taves"): "Taves_Fortier_Canna",
    ("3", "bayne"): "Bayne_Bucci_Koroma",
    ("3", "dennett"): "Dennett_Fleig-Goldstein_Friedman",
    ("3", "dienes"): "Dienes_Martin",
    ("3", "preller"): "Preller_Dumas",
    ("3", "winkelman"): "Winkelman_Fortier",
    ("4", "baird"): "Baird_Koroma",
    ("4", "carter"): "Carter_Preller",
    ("4", "gosseries"): "Gosseries_Martial",
    ("4", "hanks"): "Hanks_Mikhailova_Friedman",
    ("4", "lenggenhager"): "Lenggenhager_Ho_Milliere",
    ("4", "nichols-nichols"): "Nichols_Nichols",
    ("4", "martin-tribute"): "Fortier_ALIUS",
    ("4", "vignemont"): "Vignemont_Milliere_Serrahima",
    ("5", "martial"): "Martial",
    ("5", "canna-seligman"): "Canna_Seligman_Koroma",
    ("5", "chadha"): "Chadha_Aviles_Koroma",
    ("5", "olson-yaden"): "Olson_Yaden_Fejer",
    ("5", "schmidt"): "Schmidt_Fejer",
    ("6", "ciaunica"): "Ciaunica_Friedman_Coutrot_Koroma",
    ("6", "doss"): "Doss_Fejer",
    ("6", "gonzalez"): "Gonzalez_Koroma",
    ("6", "jillings"): "Jillings_Friedman_Coutrot_Koroma",
    ("6", "sleep"): "Koroma_Friedman_Coutrot",
    ("6", "sapolsky"): "Sapolsky_Mikhailova_Friedman",
    ("6", "skipper"): "Skipper_Roseman_Koroma_Fejer",
    ("7", "froese"): "Froese_Koroma",
    ("7", "changeux"): "Changeux_Dumas",
}


class ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_paragraph = False
        self.parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "div" and "paragraph" in (attrs_dict.get("class") or "").split():
            self.in_paragraph = True
            self.parts = []
        if self.in_paragraph and tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.in_paragraph and tag == "div":
            text = html.unescape("".join(self.parts))
            text = clean_text(text)
            if text:
                self.paragraphs.append(text)
            self.in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self.in_paragraph:
            self.parts.append(data)


@dataclass
class PieceExport:
    issue_number: str
    issue_dir: str
    slug: str
    piece_type: str
    folder_name: str
    tex_name: str
    bib_name: str
    title: str
    credit: str
    keywords: str
    abstract: str
    doi: str
    source_pdf: Path
    copied_pdf: Path
    tex_path: Path
    bib_path: Path


def to_ascii(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\u200b": "",
        "\ufeff": "",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return "".join(char for char in text if char in {"\n", "\t"} or ord(char) >= 32)


def clean_text(text: str) -> str:
    text = text.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*", "\n", text)
    return text.strip()


def compact_inline(text: str) -> str:
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def latex_escape(text: str) -> str:
    text = to_ascii(text)
    text = text.replace("\\", r"\textbackslash{}")
    replacements = {
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
    return "".join(replacements.get(char, char) for char in text)


def bib_escape(text: str) -> str:
    text = to_ascii(compact_inline(text))
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def read_issue_index() -> dict[str, Any]:
    return json.loads(ISSUE_INDEX.read_text(encoding="utf-8"))


def parse_html_metadata(source_page: str | None) -> dict[str, str]:
    if not source_page:
        return {}
    html_path = REPO_ROOT / source_page
    if not html_path.exists():
        return {}
    parser = ParagraphParser()
    parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    paragraphs = parser.paragraphs
    metadata: dict[str, str] = {}
    if paragraphs:
        metadata["title"] = compact_inline(paragraphs[0])
    if len(paragraphs) > 1:
        metadata["credit"] = compact_inline(paragraphs[1])
    for paragraph in paragraphs:
        lower = paragraph.lower()
        if "doi" in lower:
            doi_match = re.search(r"10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+", paragraph)
            if doi_match:
                metadata["doi"] = doi_match.group(0).rstrip(".,)")
            keyword_part = re.split(r"\bdoi\b\s*:?", paragraph, flags=re.IGNORECASE)[0]
            keyword_part = re.sub(r"^keywords?\s*:?", "", keyword_part, flags=re.IGNORECASE)
            keyword_part = compact_inline(keyword_part)
            if keyword_part:
                metadata["keywords"] = keyword_part
        if lower.startswith("abstract"):
            metadata["abstract"] = compact_inline(re.sub(r"^abstract\s*:?", "", paragraph, flags=re.IGNORECASE))
    return metadata


def pdf_text(pdf_path: Path, max_pages: int | None = None) -> str:
    chunks: list[str] = []
    with fitz.open(pdf_path) as doc:
        page_count = len(doc) if max_pages is None else min(len(doc), max_pages)
        for page_index in range(page_count):
            text = doc[page_index].get_text("text")
            chunks.append(clean_text(text))
    return clean_text("\n\n".join(chunks))


def parse_pdf_metadata(pdf_path: Path) -> dict[str, str]:
    text = pdf_text(pdf_path, max_pages=2)
    metadata: dict[str, str] = {}
    doi_match = re.search(r"10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+", text)
    if doi_match:
        metadata["doi"] = doi_match.group(0).rstrip(".,)")
    abstract_match = re.search(r"Abstract\s+(.*?)(?:Keywords?:|Cite as:|ALIUS Bulletin)", text, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        metadata["abstract"] = compact_inline(abstract_match.group(1))
    keyword_match = re.search(r"Keywords?:\s*(.*?)(?:\n\n|ALIUS Bulletin|$)", text, re.IGNORECASE | re.DOTALL)
    if keyword_match:
        metadata["keywords"] = compact_inline(keyword_match.group(1))
    lines = [compact_inline(line) for line in text.splitlines() if compact_inline(line)]
    if lines and "title" not in metadata:
        metadata["title"] = lines[0]
    if len(lines) > 1 and "credit" not in metadata:
        credit_lines: list[str] = []
        for line in lines[1:8]:
            if re.search(r"\b(Cite as|Abstract|Keywords?)\b", line, re.IGNORECASE):
                break
            credit_lines.append(line)
        metadata["credit"] = " / ".join(credit_lines)
    return metadata


def ensure_project_root(target_root: Path) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    for name in TOP_LEVEL_FOLDERS:
        (target_root / name).mkdir(exist_ok=True)
    extra_dirs = [item.name for item in target_root.iterdir() if item.is_dir() and item.name not in set(TOP_LEVEL_FOLDERS)]
    if extra_dirs:
        raise RuntimeError(f"Unexpected top-level folders in {target_root}: {', '.join(extra_dirs)}")


def safe_clear_dir(path: Path, project_root: Path) -> None:
    resolved_project = project_root.resolve()
    resolved_path = path.resolve()
    if resolved_project != resolved_path and resolved_project not in resolved_path.parents:
        raise RuntimeError(f"Refusing to clear outside project root: {resolved_path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def issue_dir_name(issue_number: str) -> str:
    return f"Issue{int(issue_number):02d}"


def fallback_folder_name(issue_number: str, slug: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "", slug.title().replace("-", "_")) or f"Issue{issue_number}_Piece"


def extract_text_paragraphs(text: str) -> list[str]:
    text = to_ascii(text)
    raw_blocks = re.split(r"\n\s*\n+", text)
    paragraphs: list[str] = []
    for block in raw_blocks:
        block = compact_inline(block)
        if block:
            paragraphs.append(block)
    return paragraphs


def write_tex(piece: PieceExport, extracted_text: str) -> None:
    pdf_rel = f"Shared-assets/original-pdfs/{piece.issue_dir}/{piece.source_pdf.name}"
    fallback_paragraphs = extract_text_paragraphs(extracted_text)
    fallback_body = "\n\n".join(rf"\noindent {latex_escape(paragraph)}\par" for paragraph in fallback_paragraphs)
    tex = rf"""% !TeX program = pdflatex
% ALIUS Bulletin standalone facsimile source.
% Compile from the ALIUS-bulletin project root for exact visual fidelity.
% If the shared PDF asset is absent, this file falls back to extracted text.
\providecommand{{\ALIUSRootPrefix}}{{}}

\ifdefined\ALIUSIssueBuild
  \IfFileExists{{\ALIUSRootPrefix {pdf_rel}}}{{%
    \includepdf[pages=-,fitpaper=true]{{\ALIUSRootPrefix {pdf_rel}}}%
  }}{{%
    \typeout{{ALIUS warning: missing source PDF {pdf_rel}}}%
  }}%
  \expandafter\endinput
\fi

\documentclass[a4paper,11pt]{{article}}
\usepackage[margin=22mm]{{geometry}}
\usepackage{{pdfpages}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{microtype}}
\usepackage{{parskip}}
\title{{{latex_escape(piece.title)}}}
\author{{{latex_escape(piece.credit)}}}
\date{{ALIUS Bulletin {latex_escape(piece.issue_number)}}}
\begin{{document}}
\IfFileExists{{\ALIUSRootPrefix {pdf_rel}}}{{%
  \includepdf[pages=-,fitpaper=true]{{\ALIUSRootPrefix {pdf_rel}}}%
}}{{%
  \maketitle
  \section*{{Metadata}}
  \textbf{{Piece type:}} {latex_escape(piece.piece_type)}\par
  \textbf{{DOI:}} {latex_escape(piece.doi or "not recorded")}\par
  \textbf{{Keywords:}} {latex_escape(piece.keywords or "not recorded")}\par
  \section*{{Abstract}}
  {latex_escape(piece.abstract or "No abstract was recovered from the source metadata.")}\par
  \section*{{Extracted Text}}
  \begingroup
  \small
  {fallback_body}
  \endgroup
}}%
\end{{document}}
"""
    piece.tex_path.write_text(tex, encoding="ascii", errors="strict")


def bib_authors_from_folder(folder_name: str) -> str:
    names = folder_name.replace("_", " and ").replace("-", "-")
    return names or "ALIUS Bulletin Contributors"


def write_bib(piece: PieceExport) -> None:
    key = f"alius-issue{int(piece.issue_number):02d}-{piece.slug}".replace("_", "-")
    doi_line = f"  doi = {{{bib_escape(piece.doi)}}},\n" if piece.doi else ""
    url_line = f"  url = {{https://doi.org/{bib_escape(piece.doi)}}},\n" if piece.doi else ""
    bib = (
        f"@misc{{{key},\n"
        f"  author = {{{{{bib_escape(bib_authors_from_folder(piece.folder_name))}}}}},\n"
        f"  title = {{{bib_escape(piece.title)}}},\n"
        f"  howpublished = {{ALIUS Bulletin, issue {bib_escape(piece.issue_number)}}},\n"
        f"  note = {{{bib_escape(piece.credit)}}},\n"
        f"{doi_line}"
        f"{url_line}"
        f"}}\n"
    )
    piece.bib_path.write_text(bib, encoding="ascii", errors="strict")


def render_page(pdf_path: Path, page_index: int, dpi: int) -> Image.Image:
    with fitz.open(pdf_path) as doc:
        page = doc[page_index]
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def compare_pdfs(reference_pdf: Path, candidate_pdf: Path, dpi: int, max_pages: int | None) -> dict[str, Any]:
    with fitz.open(reference_pdf) as reference_doc, fitz.open(candidate_pdf) as candidate_doc:
        page_total = min(len(reference_doc), len(candidate_doc))
        if max_pages is not None:
            page_total = min(page_total, max_pages)
        page_diffs: list[dict[str, float | int]] = []
        for page_index in range(page_total):
            reference = render_page(reference_pdf, page_index, dpi)
            candidate = render_page(candidate_pdf, page_index, dpi)
            if reference.size != candidate.size:
                target = (min(reference.width, candidate.width), min(reference.height, candidate.height))
                reference = reference.resize(target)
                candidate = candidate.resize(target)
            ref_arr = np.asarray(reference, dtype=np.int16)
            cand_arr = np.asarray(candidate, dtype=np.int16)
            diff = np.abs(ref_arr - cand_arr)
            page_diffs.append(
                {
                    "page": page_index + 1,
                    "mean_abs": round(float(diff.mean() / 255.0), 6),
                    "changed_ratio": round(float((diff.max(axis=2) > 16).mean()), 6),
                }
            )
        reference_sizes = [(round(page.rect.width, 2), round(page.rect.height, 2)) for page in reference_doc]
        candidate_sizes = [(round(page.rect.width, 2), round(page.rect.height, 2)) for page in candidate_doc]
    page_size_match = (
        len(reference_sizes) == len(candidate_sizes)
        and all(
            abs(reference_sizes[index][0] - candidate_sizes[index][0]) <= 0.5
            and abs(reference_sizes[index][1] - candidate_sizes[index][1]) <= 0.5
            for index in range(len(reference_sizes))
        )
    )
    max_changed_ratio = max((page["changed_ratio"] for page in page_diffs), default=0)
    max_mean_abs = max((page["mean_abs"] for page in page_diffs), default=0)
    return {
        "reference_page_count": len(reference_sizes),
        "candidate_page_count": len(candidate_sizes),
        "page_count_match": len(reference_sizes) == len(candidate_sizes),
        "page_size_match": page_size_match,
        "pages_compared": page_total,
        "max_changed_ratio": max_changed_ratio,
        "max_mean_abs": max_mean_abs,
        "visual_pass": len(reference_sizes) == len(candidate_sizes)
        and page_size_match
        and max_changed_ratio <= 0.06
        and max_mean_abs <= 0.015,
        "page_diffs": page_diffs,
    }


def run_pdflatex(main_tex: Path, target_root: Path, build_dir: Path) -> tuple[int, str, Path]:
    build_dir.mkdir(parents=True, exist_ok=True)
    job_name = main_tex.stem
    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-jobname={job_name}",
        str(main_tex.relative_to(target_root)),
    ]
    result = subprocess.run(
        command,
        cwd=target_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    root_pdf = target_root / f"{job_name}.pdf"
    target_pdf = build_dir / f"{main_tex.stem}.pdf"
    if root_pdf.exists():
        shutil.move(str(root_pdf), str(target_pdf))
    for extension in ["aux", "log", "out", "toc", "fls", "fdb_latexmk"]:
        candidate = target_root / f"{job_name}.{extension}"
        if candidate.exists():
            candidate.unlink()
    return result.returncode, result.stdout, target_pdf


def write_issue_file(issue: dict[str, Any], pieces: list[PieceExport], target_root: Path) -> Path:
    issue_name = f"issue{int(issue['issue_number']):02d}.tex"
    issue_path = target_root / "Bulletins" / issue_name
    input_lines = [
        rf"\input{{Interviews/{piece.issue_dir}/{piece.folder_name}/{piece.tex_name}}}"
        for piece in pieces
    ]
    title = f"ALIUS Bulletin issue {issue['issue_number']}"
    tex = rf"""% !TeX program = pdflatex
% Compile this from the ALIUS-bulletin project root.
\documentclass[a4paper]{{article}}
\usepackage[margin=0pt]{{geometry}}
\usepackage{{pdfpages}}
\newcommand{{\ALIUSIssueBuild}}{{1}}
\begin{{document}}
% {latex_escape(title)} assembled from standalone interview files.
{chr(10).join(input_lines)}
\end{{document}}
"""
    issue_path.write_text(tex, encoding="ascii", errors="strict")
    return issue_path


def export_instructions(target_root: Path) -> list[Path]:
    instructions_root = target_root / "Instructions"
    instructions_root.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for basename in INSTRUCTION_BASENAMES:
        for extension in [".tex", ".pdf"]:
            source = REFERENCE_DOCS_ROOT / f"{basename}{extension}"
            if not source.exists():
                raise FileNotFoundError(source)
            destination = instructions_root / source.name
            shutil.copy2(source, destination)
            copied.append(destination)
    return copied


def write_manifest(exports: list[PieceExport], issue_paths: list[Path], target_root: Path) -> None:
    instruction_files = sorted((target_root / "Instructions").glob("*"))
    manifest = {
        "schema_version": 1,
        "project_root": str(target_root),
        "top_level_folders": TOP_LEVEL_FOLDERS,
        "pieces": [
            {
                "issue": piece.issue_dir,
                "slug": piece.slug,
                "piece_type": piece.piece_type,
                "folder": str(piece.tex_path.parent.relative_to(target_root)),
                "tex": str(piece.tex_path.relative_to(target_root)),
                "bib": str(piece.bib_path.relative_to(target_root)),
                "pdf": str(piece.tex_path.with_suffix(".pdf").relative_to(target_root)),
                "source_pdf": str(piece.copied_pdf.relative_to(target_root)),
                "doi": piece.doi,
            }
            for piece in exports
        ],
        "bulletins": [str(path.relative_to(target_root)) for path in issue_paths],
        "bulletin_pdfs": [str(path.with_suffix(".pdf").relative_to(target_root)) for path in issue_paths],
        "instructions": [str(path.relative_to(target_root)) for path in instruction_files if path.is_file()],
    }
    (target_root / "Shared-assets" / "project-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="ascii", errors="strict"
    )


def export_project(target_root: Path) -> tuple[list[PieceExport], list[Path]]:
    index = read_issue_index()
    ensure_project_root(target_root)
    safe_clear_dir(target_root / "Interviews", target_root)
    safe_clear_dir(target_root / "Bulletins", target_root)
    safe_clear_dir(target_root / "Shared-assets" / "original-pdfs", target_root)
    safe_clear_dir(target_root / "Shared-assets" / "qa", target_root)
    export_instructions(target_root)

    exports: list[PieceExport] = []
    issue_paths: list[Path] = []
    pieces_by_issue: dict[str, list[PieceExport]] = {}

    for issue in index["issues"]:
        issue_number = issue["issue_number"]
        issue_dir = issue_dir_name(issue_number)
        (target_root / "Interviews" / issue_dir).mkdir(parents=True, exist_ok=True)
        (target_root / "Shared-assets" / "original-pdfs" / issue_dir).mkdir(parents=True, exist_ok=True)
        for piece in issue["pieces"]:
            reference_rel = piece.get("reference_pdf")
            if not reference_rel:
                continue
            source_pdf = REPO_ROOT / reference_rel
            if not source_pdf.exists():
                raise FileNotFoundError(source_pdf)
            folder_name = FOLDER_NAMES.get((issue_number, piece["slug"]), fallback_folder_name(issue_number, piece["slug"]))
            piece_dir = target_root / "Interviews" / issue_dir / folder_name
            piece_dir.mkdir(parents=True, exist_ok=True)
            copied_pdf = target_root / "Shared-assets" / "original-pdfs" / issue_dir / source_pdf.name
            shutil.copy2(source_pdf, copied_pdf)

            html_metadata = parse_html_metadata(piece.get("source_page"))
            pdf_metadata = parse_pdf_metadata(source_pdf)
            metadata = {**pdf_metadata, **html_metadata}
            title = metadata.get("title") or piece["title"]
            credit = metadata.get("credit") or ""
            doi = metadata.get("doi") or ""
            keywords = metadata.get("keywords") or ""
            abstract = metadata.get("abstract") or ""
            export = PieceExport(
                issue_number=issue_number,
                issue_dir=issue_dir,
                slug=piece["slug"],
                piece_type=piece.get("piece_type", "piece"),
                folder_name=folder_name,
                tex_name=f"{folder_name}.tex",
                bib_name=f"{folder_name}.bib",
                title=title,
                credit=credit,
                keywords=keywords,
                abstract=abstract,
                doi=doi,
                source_pdf=source_pdf,
                copied_pdf=copied_pdf,
                tex_path=piece_dir / f"{folder_name}.tex",
                bib_path=piece_dir / f"{folder_name}.bib",
            )
            extracted_text = pdf_text(source_pdf)
            write_tex(export, extracted_text)
            write_bib(export)
            exports.append(export)
            pieces_by_issue.setdefault(issue_number, []).append(export)

    for issue in index["issues"]:
        issue_exports = pieces_by_issue.get(issue["issue_number"], [])
        if issue_exports:
            issue_paths.append(write_issue_file(issue, issue_exports, target_root))

    write_manifest(exports, issue_paths, target_root)
    return exports, issue_paths


def write_report(results: list[dict[str, Any]], issue_results: list[dict[str, Any]], target_root: Path) -> None:
    lines = [
        "# Visual Fidelity Report",
        "",
        "The standalone interview files compile in facsimile mode by including the published reference PDFs from `Shared-assets/original-pdfs`.",
        "Each interview file also contains an extracted-text fallback so a single `.tex` remains compilable when separated from shared assets.",
        "",
        "## Interview checks",
        "",
    ]
    for result in results:
        lines.append(f"### {result['name']}")
        lines.append(f"- Status: `{result['status']}`")
        if result.get("final_pdf"):
            lines.append(f"- Final PDF: `{result['final_pdf']}`")
        if result.get("comparison"):
            comparison = result["comparison"]
            lines.append(f"- Visual pass: `{comparison['visual_pass']}`")
            lines.append(f"- Page count match: `{comparison['page_count_match']}`")
            lines.append(f"- Page size match: `{comparison['page_size_match']}`")
            lines.append(f"- Max changed ratio: `{comparison['max_changed_ratio']}`")
            lines.append(f"- Max mean abs: `{comparison['max_mean_abs']}`")
        if result.get("log"):
            lines.append(f"- Log: `{result['log']}`")
        lines.append("")
    lines.extend(["## Bulletin assembly checks", ""])
    for result in issue_results:
        final_pdf = f", `{result['final_pdf']}`" if result.get("final_pdf") else ""
        lines.append(f"- `{result['name']}`: `{result['status']}` ({result.get('pages', 0)} pages{final_pdf})")
    (target_root / "Shared-assets" / "qa" / "visual-fidelity-report.md").write_text(
        "\n".join(lines), encoding="ascii", errors="strict"
    )


def validate_project(exports: list[PieceExport], issue_paths: list[Path], target_root: Path, dpi: int, max_pages: int | None) -> None:
    qa_root = target_root / "Shared-assets" / "qa"
    build_root = qa_root / "build"
    logs_root = qa_root / "logs"
    safe_clear_dir(build_root, target_root)
    logs_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for export in exports:
        build_dir = build_root / "interviews" / export.issue_dir / export.folder_name
        code, output, candidate_pdf = run_pdflatex(export.tex_path, target_root, build_dir)
        log_path = logs_root / f"{export.issue_dir}_{export.folder_name}.log.txt"
        log_path.write_text(output, encoding="utf-8", errors="replace")
        result: dict[str, Any] = {
            "name": f"{export.issue_dir}/{export.folder_name}",
            "status": "compiled" if code == 0 and candidate_pdf.exists() else "compile-failed",
            "log": str(log_path.relative_to(target_root)),
        }
        if result["status"] == "compiled":
            result["comparison"] = compare_pdfs(export.copied_pdf, candidate_pdf, dpi=dpi, max_pages=max_pages)
            final_pdf = export.tex_path.with_suffix(".pdf")
            shutil.copy2(candidate_pdf, final_pdf)
            result["final_pdf"] = str(final_pdf.relative_to(target_root))
        results.append(result)

    issue_results: list[dict[str, Any]] = []
    for issue_path in issue_paths:
        build_dir = build_root / "bulletins" / issue_path.stem
        code, output, candidate_pdf = run_pdflatex(issue_path, target_root, build_dir)
        log_path = logs_root / f"{issue_path.stem}.log.txt"
        log_path.write_text(output, encoding="utf-8", errors="replace")
        pages = 0
        if code == 0 and candidate_pdf.exists():
            with fitz.open(candidate_pdf) as doc:
                pages = len(doc)
            final_pdf = issue_path.with_suffix(".pdf")
            shutil.copy2(candidate_pdf, final_pdf)
        issue_results.append(
            {
                "name": issue_path.name,
                "status": "compiled" if code == 0 and candidate_pdf.exists() else "compile-failed",
                "pages": pages,
                "final_pdf": str(issue_path.with_suffix(".pdf").relative_to(target_root)) if code == 0 and candidate_pdf.exists() else None,
                "log": str(log_path.relative_to(target_root)),
            }
        )

    (qa_root / "visual-fidelity-results.json").write_text(
        json.dumps({"interviews": results, "bulletins": issue_results}, indent=2),
        encoding="ascii",
        errors="strict",
    )
    write_report(results, issue_results, target_root)

    failed = [item for item in results if item["status"] != "compiled"]
    failed.extend(item for item in issue_results if item["status"] != "compiled")
    if failed:
        names = ", ".join(item["name"] for item in failed)
        raise RuntimeError(f"Compilation failed for: {names}")
    if build_root.exists():
        shutil.rmtree(build_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ALIUS Bulletin interviews into the flat Overleaf project layout.")
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--dpi", type=int, default=96)
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    exports, issue_paths = export_project(args.target_root.resolve())
    if not args.skip_validation:
        validate_project(exports, issue_paths, args.target_root.resolve(), dpi=args.dpi, max_pages=args.max_pages)
    print(f"Exported {len(exports)} pieces and {len(issue_paths)} bulletin files to {args.target_root.resolve()}")


if __name__ == "__main__":
    main()
