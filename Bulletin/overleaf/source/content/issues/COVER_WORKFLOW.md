# Editable Cover Workflow

ALIUS covers are generated from shared artwork plus issue metadata.

## Shared Artwork

The common image denominator lives in `assets/cover-parts`:

- `leaf-logo.png`
- `figure.png`
- `plant.png`

Replace those three files to change the artwork globally. Keep the same file
names if you want every issue to update without editing TeX.

## Editable Text

Edit cover text in `content/issues/issue-index.json`, inside each issue's
`cover` block:

- `editors`
- `date_line`
- `website`
- `tagline`
- `subjects`

Then run:

```powershell
python scripts/sync_issue_registry.py
```

The generated Overleaf cover file is:

```text
content/issues/<issue>/cover.tex
```

## Layout Controls

Global cover positioning, font sizes, colors, and asset paths live in:

```text
project-controls.tex
```

The quickest single-cover compile target is:

```text
fixtures/covers/<issue>-cover.tex
```

For example, set `fixtures/covers/issue-06-cover.tex` as the Overleaf main file
to tune only issue 6's cover before compiling the full issue.
