## Active Site Structure

This folder is the active source of truth for the public site.

The build now revolves around seven top-level one-page sections:

- `home`
- `about`
- `team`
- `bulletin`
- `journal-club`
- `events`
- `membership`

Each section contains a single `page.html` file that the build publishes to its canonical route.

Shared sitewide assets remain in:

- `site-src/static/` for published assets
- `site-src/data/` for routing and redirect manifests

Legacy multi-page source material still exists under `site-src/content/`, but the active build no longer depends on it.
