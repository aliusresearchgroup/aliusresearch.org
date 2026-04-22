#!/usr/bin/env python
from __future__ import annotations

import subprocess
from pathlib import Path

from docx import Document


REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "assets" / "reference-docs"
SOURCE_DIR = REPO_ROOT / "internal_documents" / "ALIUS Bulletin"


REFERENCE_SOURCES = [
    SOURCE_DIR / "Template_ALIUS_Bulletin.docx",
    SOURCE_DIR / "Guidelines" / "ALIUS Bulletin - Guidelines for Interviews - 2022.docx",
    SOURCE_DIR / "Guidelines" / "ALIUS Bulletin - Guidelines for conversations - 2022.docx",
    SOURCE_DIR / "Guidelines" / "ALIUS Bulletin - Guidelines for Commentary - 2022.docx",
    SOURCE_DIR / "Guidelines" / "ALIUS Bulletin - Guidelines for podcast - 2022.docx",
    SOURCE_DIR / "Guidelines" / "ALIUS Bulletin - Guidelines for reviews - 2022.docx",
]


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


def extract_lines(path: Path) -> list[str]:
    doc = Document(str(path))
    lines = []
    for para in doc.paragraphs:
        text = para.text.replace("\u200b", "").strip()
        if text:
            lines.append(text)
    return lines


def write_reference_tex(title: str, lines: list[str], output_path: Path) -> None:
    body = []
    for line in lines:
        if len(line) < 80 and line.upper() == line:
            body.append(r"\section*{" + tex_escape(line.title()) + "}")
        else:
            body.append(tex_escape(line) + r"\par")
            body.append("")
    tex = "\n".join(
        [
            r"\documentclass[11pt]{article}",
            r"\usepackage[a4paper,margin=25mm]{geometry}",
            r"\usepackage{fontspec}",
            r"\usepackage[hidelinks]{hyperref}",
            r"\setmainfont{Latin Modern Roman}",
            r"\pagestyle{plain}",
            r"\begin{document}",
            r"{\LARGE\bfseries " + tex_escape(title) + r"\par}",
            r"\vspace{1em}",
            *body,
            r"\end{document}",
            "",
        ]
    )
    output_path.write_text(tex, encoding="utf-8")


def write_editor_checklist(output_path: Path) -> None:
    tex = "\n".join(
        [
            r"\documentclass[11pt]{article}",
            r"\usepackage[a4paper,margin=25mm]{geometry}",
            r"\usepackage{enumitem}",
            r"\usepackage{fontspec}",
            r"\setmainfont{Latin Modern Roman}",
            r"\begin{document}",
            r"{\LARGE\bfseries ALIUS Bulletin Editor Checklist\par}",
            r"\vspace{1em}",
            r"\begin{itemize}[leftmargin=1.5em]",
            r"\item Confirm the piece subtype: interview, conversation, podcast, commentary, review, or editorial note.",
            r"\item Keep the published bulletin look as the visual target, not the working Word-template look.",
            r"\item Provide a title, abstract, keywords, contributor block, citation block, and running title.",
            r"\item Keep pull quotes explicit and editor-approved. For interviews and conversations, aim for 2--6 excerpts.",
            r"\item Use American-English punctuation conventions, straight ALIUS spacing rules, and APA references.",
            r"\item Check front-matter wording carefully because historical issues differ in small human-edited ways.",
            r"\item Run the local preflight and validation scripts before publishing a new standardized PDF.",
            r"\end{itemize}",
            r"\end{document}",
            "",
        ]
    )
    output_path.write_text(tex, encoding="utf-8")


def compile_tex(tex_path: Path) -> None:
    subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "-file-line-error",
            "-output-directory",
            str(OUTPUT_DIR),
            str(tex_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source in REFERENCE_SOURCES:
        lines = extract_lines(source)
        stem = source.stem.lower().replace(" ", "-")
        tex_path = OUTPUT_DIR / f"{stem}.tex"
        write_reference_tex(source.stem, lines, tex_path)
        compile_tex(tex_path)
    checklist_path = OUTPUT_DIR / "editor-checklist.tex"
    write_editor_checklist(checklist_path)
    compile_tex(checklist_path)


if __name__ == "__main__":
    main()

