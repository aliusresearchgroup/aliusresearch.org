# Maintenance Audit 2026-03-13

## Goal

Improve site loading efficiency without changing frontend design, isolate unused material into `archive/`, and leave the repository easier to maintain.

## Active structure

- `site-src/`: editable source data and static assets used to build the site.
- `docs/`: generated GitHub Pages output.
- `tools/migrate/`: build pipeline and HTML publish optimizations.
- `tools/audit/`: verification scripts for links and unused static assets.
- `migration/`: generated reports and migration/audit artifacts.
- `archive/`: retired build outputs, inactive workspaces, unused assets, and preserved originals.

## Changes made

- Removed duplicated generated resource includes during publish.
- Stripped unused customer-account runtime from published HTML.
- Added lazy loading and async decoding to content images during publish.
- Added `font-display: swap` to bundled font stylesheets.
- Re-encoded the live background image at `uploads/9/1/6/0/91600416/background-images/1366250879.jpg` and kept the original in `archive/optimized-originals/20260313/`.
- Moved unused static files and stale `*.prev-*` folders into `archive/unused-static/20260313/`.
- Moved root-level `docs-prev-*` directories into `archive/docs-builds/20260313/`.
- Moved the inactive nested `aliusresearch.org/` workspace into `archive/inactive-workspaces/20260313/`.
- Updated the site config for GitHub Pages custom-domain publishing so rebuilt output stays rooted at `/` and `docs/CNAME` is generated for `aliusresearch.org`.

## Verification

- Build output summary: `migration/build-summary.txt`
- Link audit: `migration/link-check-issues.csv`
- Unused static asset audits:
  - `migration/unused-static-assets.csv`
  - `migration/unused-static-assets-post-domain-fix.csv`
  - `migration/unused-static-assets-post-clean.csv`
  - `migration/unused-static-assets-final.csv`

## Results

- Final link check reported `0` missing local links/assets across `289` generated HTML files.
- Final unused-static audit reported `0` unused files remaining in the active static tree.
- Live publish output keeps the existing design while loading fewer unnecessary resources on first paint.
