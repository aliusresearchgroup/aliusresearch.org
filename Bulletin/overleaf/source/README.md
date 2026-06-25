# ALIUS Bulletin Overleaf Template

This project is a repo-contained LaTeX reconstruction and standardization system for ALIUS Bulletin. It is designed to be uploadable to Overleaf, compiled with `latexmk -lualatex`, and stress-tested against the published bulletin PDFs in the main repository.

## What Is Here

- `aliusbulletin.cls`
  Shared layout, typography, page-style, and semantic body macros.
- `assets/fonts`
  Vendored `Lato` and `Cormorant Garamond` font files for portable builds.
- `assets/covers`
  Known issue cover assets from the ALIUS corpus.
- `assets/cover-parts`
  Deconstructed shared cover artwork used by `\AliusRenderIssueCover`: leaf
  logo, anatomical figure, and plant. Cover text stays editable in LaTeX.
- `assets/reference-docs`
  Generated guideline/template reference PDFs for editors.
- `content/pieces`
  Metadata and body files for reconstructed bulletin pieces.
- `content/issues`
  Issue-level registry data, front matter, and per-issue assembly files.
- `content/issues/issue-index.json`
  Canonical index of all bulletin editions, their source HTML, reference PDFs,
  known cover assets, and piece-level reconstruction status.
- `content/rules`
  Optional editor-facing annotation rules. They render only when
  `\AliusShowRuleAnnotations` is enabled.
- `fixtures/pieces`
  Standalone compilable sample pieces.
- `fixtures/issues`
  Standalone compilable issue bundles.
- `scripts`
  Extraction, preflight, rendering, reference-build, and validation utilities.

## Compile Locally

Run these commands from this folder:

```powershell
latexmk -lualatex fixtures/pieces/gonzalez.tex
latexmk -lualatex fixtures/pieces/froese.tex
latexmk -lualatex fixtures/issues/issue-05.tex
```

The default `latexmkrc` writes outputs into `build/`.

## Overleaf Usage

Upload the whole `Bulletin/overleaf/source` folder as a project when you want
the full reconstruction workflow, fixtures, scripts, and reference material.
For the editor-facing compact Overleaf package, use `Bulletin/overleaf/export`.

- Set the desired file under `fixtures/pieces` or `fixtures/issues` as the main file.
- Or set `content/issues/<issue>/main.tex` as the main file for an issue-centered project.
- Use `fixtures/covers/<issue>-cover.tex` to compile only a generated,
  editable cover page.
- Use the semantic body macros in the `content/pieces/<slug>/body.tex` files.
- Keep editorial notes and reference PDFs inside `assets/reference-docs`.

## Source Model

Each piece is split into two files:

- `meta.tex`
  Visual and bibliographic metadata: title, subtitle, credit line, citation block, contributors, abstract, keywords, running title, and local overrides.
- `body.tex`
  Structured content using semantic macros such as `\AliusQuestion{...}`, `\AliusAnswer{...}`, `\AliusSpeakerAnswer{...}{...}`, `\AliusParagraph{...}`, `\AliusPullQuote{...}`, and `\AliusReferenceEntry{...}`.

This keeps the template Overleaf-friendly while still allowing local automation to lint and validate the sources.

## Issue Registry Workflow

All seven published bulletin editions are indexed in `content/issues/issue-index.json`.
Each issue can include a `cover` block with editable cover metadata:
`editors`, `date_line`, `website`, `tagline`, and `subjects`.
See `content/issues/COVER_WORKFLOW.md` for the cover-only workflow.
Run the sync script whenever that registry or a piece reconstruction status changes:

```powershell
python scripts/sync_issue_registry.py
```

The sync script writes:

- `content/issues/<issue>/issue.json`
- `content/issues/<issue>/main.tex`
- `content/issues/<issue>/README.md`
- `content/issues/<issue>/cover.tex`
- `fixtures/issues/<issue>.tex`
- `fixtures/covers/<issue>-cover.tex`
- `fixtures/all-issues-manifest.json`

Only issue folders marked `reconstructed` are treated as final visual-fidelity
targets by default. Partial folders still compile reconstructed pieces inside an
edition scaffold, which is useful while integrating individual interviews into
their proper bulletin issue.

## Validation Workflow

```powershell
python scripts/build_reference_docs.py
python scripts/sync_issue_registry.py
python scripts/preflight_editorial.py --manifest fixtures/fixture-manifest.json
python scripts/validate_bulletins.py --manifest fixtures/fixture-manifest.json --save-renders
python scripts/validate_bulletins.py --manifest fixtures/cover-manifest.json --save-renders
python scripts/run_visual_fidelity_loop.py --manifest fixtures/fixture-manifest.json
```

The validator:

- compiles each fixture with `latexmk -lualatex`
- checks page size, page count, and embedded-font presence
- rasterizes candidate and reference PDFs
- computes page-level diffs with `PIL` and `numpy`
- optionally saves candidate/reference page PNGs for visual inspection
- writes ranked Markdown reports and per-page diff images

## Current Canonical Fixture Set

- `issue-05` full bundle
- `gonzalez` interview
- `sleep` podcast
- `martial` commentary
- `olson-yaden` conversation
- `canna-seligman` interview
- `chadha` interview
- `schmidt` interview
- `froese` interview

This is the baseline set used for the first reconstruction and calibration loop.
