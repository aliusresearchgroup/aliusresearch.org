# ALIUS Bulletin Overleaf Template

This is the editor-facing Overleaf project for future ALIUS bulletin work.

It is organized in two layers:

- `pieces/`
  Each interview or article lives in its own folder with a `meta.tex` file and a `body.tex` file.
- `issues/`
  Each full bulletin issue has its own front matter and table of contents, then includes one or more piece folders.
- `project-controls.tex`
  Global palette and layout controls for the template. This is the first place to edit if you want to move cover elements, tune the greens, or adjust reusable design parameters.
- `trials/`
  Small calibration mains that recreate real issue-family covers so you can compare the template against published bulletin artwork before changing the live project files.

## Main Files

- `main-piece.tex`
  Compile this when you want to preview or edit one interview on its own.
- `main-issue.tex`
  Compile this when you want to assemble a full bulletin from multiple piece folders.

## Recommended Workflow

1. Duplicate `pieces/00-template/` and rename it to your new piece slug.
2. Fill in `meta.tex` with the title, subtitle, citation, DOI line, abstract, keywords, and contributor details.
3. Fill in `body.tex` with:
   - `\AliusQuestion{...}`
   - `\AliusAnswer{...}`
   - `\AliusPullQuote{...}` near the relevant answer
   - `\AliusSectionHeading{References}`
   - `\AliusReferenceEntry{...}`
4. Point `main-piece.tex` at the new folder while you edit.
5. When the piece is ready, include it in `main-issue.tex` and add a TOC entry in `issues/00-template/frontmatter.tex`.

## Editable Cover System

The issue cover is no longer a flat imported cover image by default. It is built from:

- editable text fields for issue number, date, editors, website, and interviewed names
- reusable artwork assets in `assets/cover-parts/`
- palette and positioning controls in `project-controls.tex`

This means you can change:

- the names shown on the cover
- the date or year shown on the cover
- the editor line
- the wordmark text, size, and line gap
- the green shades
- the positions of the logo, title, names, figure, plant, and bottom labels
- the font size and spacing of the cover names, issue number, date line, and website
- the curve of the bottom black panel
- the body, question, reference, and pull-quote typography

## Standardization

The typography, colors, margins, headers, footers, and front-matter layout live in `aliusbulletin.cls`.

That means editors mostly work in the content files, while layout-sensitive adjustments can be made centrally through `project-controls.tex` and the issue metadata files.

## Cover Metadata

Each issue front matter reads `issues/<issue-folder>/issue-meta.tex`.

That file controls:

- issue number
- issue span or year
- cover date line
- website
- editor line
- ordered cover subject names

The cover subject names are intentionally manual rather than inferred so editors can exactly control the people listed on the cover and the order in which they appear.

## Reference Material

The `assets/reference-docs/` folder contains guideline and legacy template reference PDFs that can be uploaded to Overleaf alongside this project.
