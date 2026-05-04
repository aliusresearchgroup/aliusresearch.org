# ALIUS Redesign Checkpoints

This log catalogs pushed redesign checkpoints so individual features can be
reverted selectively if they do not work for the organization.

| Checkpoint | Commit | Scope | Verification | Revert Notes |
|---|---|---|---|---|
| checkpoint-001 | this commit | Installed Pretext skills; created top-level page folders; wired shared assets; added sticky seven-tab nav, left/page anchors, Team data extraction, obfuscated email PNGs, and Pretext-enhanced Team expansion. | Build passed; link check passed (`278` HTML files, `0` missing local links/assets); Playwright visual QA passed at desktop/tablet/mobile for all seven routes plus Team expand/email/Escape checks. | Revert this checkpoint to remove the folder migration, shared redesign layer, and first Team-grid interaction pass. |
