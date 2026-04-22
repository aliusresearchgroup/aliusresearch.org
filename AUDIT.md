# aliusresearch.org — UX/UI refresh audit

Prioritised findings from direct review of the source + built site. Each
item lists impact (HIGH/MEDIUM/LOW) · effort (S/M/L) · target files.

## HIGH impact

### H1 — Flatten the legacy `/uploads/9/1/6/0/91600416/` tree to `/uploads/` · M
**Files:** `docs/uploads/**`, `site-src/static/uploads/**`, ~750 HTML/CSS/JS
files referencing the legacy path.
**Why:** paths like `/uploads/9/1/6/0/91600416/background-images/1366250879.jpg`
are hostile to editing, version control, and manual updates. The first attempt
broke 166 links because some referenced files weren't under the legacy tree —
a second pass needs a wider source scan (e.g. include any file referenced in
HTML as `/uploads/...`, not just files physically under the legacy root).

### H2 — Mirror folder structure to navigation (assets colocated with their page) · L
**Files:** add `docs/assets/{team,bulletin,events,about,membership,shared}/...`
**Why:** the user explicitly wants per-page asset grouping (e.g.
`assets/team/members/george-fejer/portrait.jpg`). Today everything lives in
one flat `/media/images/` or in `/uploads/.../`. Proposed layout is in §§
below — needs one cautious migration PR.

### H3 — Legacy `docs/*.html` stubs (e.g. `docs/events.html`, `docs/team.html`) · S
**Files:** `docs/about.html`, `docs/team.html`, `docs/bulletin01..07.html`,
`docs/team-222796.html`, etc. (~60 files at the root of `docs/`).
**Why:** these are redirect stubs from the pre-consolidation era. They take
up space and clutter the file tree. The consolidated `/bulletin/`, `/team/`
etc. routes are what the nav points to; the stubs only catch direct URL hits.
Keep them for redirect compatibility but move them to a `docs/_redirects/`
subfolder and serve via a 301 mechanism where possible. (GitHub Pages has no
server redirects, so file-based stubs stay — just organise them better.)

### H4 — Individual team-member sub-pages served but unreachable · S
**Files:** `docs/about/team/team-639772/`, `team-743740/`, `team-814948/`,
`team-912849/`, `team-955042-710461/` etc. remain in the docs/ output.
**Why:** the consolidated `/team/` no longer links to these; they're dead
pages still being generated. Either add them to `redirects.json` pointing at
`/team/#member-<slug>` or delete the corresponding entries from
`pages.json` so the build stops emitting them.

## MEDIUM impact

### M1 — About page `<br><br>` walls of text · M
**Files:** `site-src/content/about/body.html`,
`site-src/content/about/original.rewritten.html`.
**Why:** the body is rendered as one `<div class="paragraph">` with `<br>`
separators — no real paragraph semantics. Already scoped-styled with
72ch / line-height 1.72, but future content work should transform these into
real `<p>` elements and introduce `<h3>` subsection breaks.

### M2 — Research projects page (`/research/`) layout · M
**Files:** `site-src/content/research/projects/*/body.html`.
**Why:** each project page still uses Weebly-generated multicol tables with
inline styles, width/height on every image, and centered text. These pages
would benefit from the same "card grid" treatment the team page got — one
project card per row with title + summary + lead researchers + link to
full writeup.

### M3 — Typography mix (Raleway + Gentium Basic + Playfair Display) · S
**Files:** all `head.raw.html` fragments, `main_style.css`.
**Why:** three fonts is one too many. The team page now uses Raleway only;
propagate that to the rest of the site or formalise the role of each font
(Raleway for headings/UI, Gentium Basic for body prose) in a single
`typography-scale.css`. Currently the rule is implicit and inconsistent.

### M4 — Duplicate member listings · M
**Files:** `docs/members1.html`, `docs/researcher-members.html`,
`docs/team-222796.html`, `docs/team-955042.html`, plus the consolidated
`/team/`.
**Why:** five pages currently describe "the team" with overlapping content.
Only `/team/` should remain; the others should redirect there (some already
do via `redirects.json`).

### M5 — Image heights hard-coded as inline styles · M
**Files:** Weebly-exported pages contain `style="width:218;max-width:100%"`
and friends everywhere.
**Why:** these override responsive CSS and produce distorted images on
narrow screens. Strip `style="width:<N>"` from `<img>` in all body fragments
during the build; rely on CSS + natural aspect ratios instead.

### M6 — Header/nav rendering inconsistency on legacy root stubs · S
**Files:** `docs/1.html`, `docs/2.html`, `docs/oldcode.html`.
**Why:** these generate a header via the build but the body is effectively
empty. Either redirect or add meaningful content. Low-visibility but cheap
to fix.

## LOW impact

### L1 — `docs/assets/vendor/editmysite/...` is still ~4MB of vendored Weebly · M
Consolidate the editmysite vendor JS (main.js 470KB is the biggest) — some
parts are only relevant to customer-accounts which we already stripped.

### L2 — `.vscode/` and `.claude/` committed · S
Both directories are user-local; add them to `.gitignore`.

### L3 — Redirect stubs with query strings lost · S
`/published/gfejer_2.png?1744132228` referenced with a cache-buster that
doesn't map to a file after flatten. Strip the `?<timestamp>` suffix before
resolving, or keep the original URL intact.

### L4 — The horizontal top nav underlines (decorative lines around HOME…)
look like orphaned Weebly template artefacts on mobile · S
Use media queries to collapse the decorative `<hr>` elements on <640px.

### L5 — `_orig` and `-orig` image filename duplicates · S
Many images have both an `X.png` and `X-orig.png` where `-orig` is the
uncompressed original. The build wraps a `<picture>` around compressed
variants but the originals are still served. Move the `-orig` duplicates
into `docs/archive/images-preoptimization/` and update references.

## Proposed asset-folder reorganisation (for approval)

```
docs/assets/
  shared/
    alius-logo.png          (was /uploads/9/1/6/0/91600416/1477332210.png)
    background.jpg          (was /uploads/9/.../background-images/…)
    fonts/…                 (was /assets/vendor/editmysite/cdn2.editmysite.com/fonts/)
    vendor/                 (minified Weebly JS/CSS we actually need)
  about/                    (about-page-specific assets, if any)
  team/
    members/
      george-fejer/
        portrait.jpg
        cv.pdf
      brendan-fleig-goldstein/
        portrait.jpg
      …
  bulletin/
    issues/
      bulletin-01/          (cover + PDFs for that issue)
      bulletin-02/
      …
    interviews/             (shared interview assets)
  events/
    assc-satellite-2025/    (photos, flyers)
    symposia/
    journal-club/
  membership/
```

Migration strategy (safe):
1. Build a manifest: `source-path → destination-path`
2. Copy files to new locations (originals stay for safety)
3. Rewrite references in HTML/CSS/JS to new paths
4. Rebuild + link-check with 0 errors before deleting originals
5. Add 301 redirects for the most-linked legacy paths (the logo, CV PDFs)

**Request for you:** approve/edit the layout above and I'll ship it as the
next checkpoint.

---

*Audit written 2026-04-22 against commit 960a8b0. A second-opinion audit from
a background agent is in progress; findings will be merged once it returns.*
