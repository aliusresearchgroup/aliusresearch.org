# Archive

This folder holds material intentionally removed from the live website and source tree.

## Rules

- Keep archived content out of `docs/` and `site-src/static/`.
- Use dated subfolders in `YYYYMMDD` format for new archive batches.
- Preserve original relative paths inside each dated batch so items can be restored safely if needed.
- Do not edit files in place here unless the goal is archival documentation.

## Folder layout

- `docs-builds/`: previous generated `docs` snapshots moved out of the repo root.
- `inactive-workspaces/`: inactive nested site copies or abandoned working directories.
- `optimized-originals/`: originals kept before replacing a live file with a smaller equivalent.
- `unused-static/`: static files confirmed unused by audit and removed from the live asset tree.
- `weebly-export/`: retained legacy export material that is not part of the current publish path.

## Restore process

1. Move the needed file back into its original location under `site-src/static/` or another active source folder.
2. Rebuild the site with `tools/migrate/build-site.ps1`.
3. Re-run `tools/audit/find-unused-static-assets.ps1` and `tools/audit/link-check.ps1`.
4. Confirm the restored asset is referenced by generated files in `docs/`.
