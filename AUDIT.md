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

## Second-opinion audit (deep crawl, 2026-04-22)

Independent findings from a deeper file-by-file crawl. Numbered A-n to avoid
collisions with the list above.

### HIGH impact

**A1 · Ko-fi iframes still live in Bulletin** — my earlier purge caught
`<script src=...ko-fi...>` but not `<iframe id='kofiframe' src='https://ko-fi.com/…'>`.
Two widgets still render between bulletin issues (lines 388 and 457 of
`_consolidated/bulletin/body.html`).

**A2 · Each consolidated page bundles the IntersectionObserver
active-section script 7 times**, observing IDs that only exist on OTHER pages.
Keep one, scope the selector to the current page.

**A3 · `pretext-nav-fit.js` loaded 3 times per consolidated page** → 3 resize
listeners, 3 esm.sh fetches. Load once.

**A4 · Team card bios start with orphan email fragments** (`"neuro [dot] "`,
`"alessio [dot] "`, etc.) in ~11 cards. An HTML sanitiser stripped the
`<a mailto>` but left its visible text mid-sentence. Trim bio until the first
capitalised word OR re-extract bios from the original rewritten source.

**A5 · About-page half-linkified** — my regex missed Jackendoff, Baars,
Marti, Maupertuis, Moreau, Corlett/Frith, Studerus/Gamma, Hobson. It also
linkified *journal names* instead of paper titles, and double-encoded
apostrophes (`%26rsquo%3B`). Plus a leftover Weebly `<span>Jac</span><font>kendoff`
splits the name.

**A6 · Legacy partials still present** — `site-src/partials/nav-desktop.raw.html`
(1727 lines) and `nav-mobile.raw.html` (342 lines) hold the pre-consolidation
dropdown tree. Bodies already inline their own nav; these partials are dead
weight, risk being re-included.

**A7 · Orphan content directories with byte-identical duplicates**:
`events/journal-club-228113`, `events/journal-club-995321`,
`events/journalclub-868968` are all byte-identical 9711-line copies of
`events/journal-club`. Same for bulletin duplicates with long numeric
suffixes and for `teamtest*`/`teamtemplate-956529`.

**A8 · Broken Weebly newsletter form on `/journal-club/`** — posts to
`//www.weebly.com/weebly/apps/formSubmit.php` (dead endpoint). Visitors
think they subscribed; their email goes nowhere.

**A9 · `/journal-club/` and `/events/journal-club/` both build with
diverging HTML** — SEO dup content. Pick one canonical URL (top nav goes to
`/journal-club/`) and 301 the other.

### MEDIUM impact

**A10 · Team page’s `.team-section-heading` CSS is defined but never used.**
Current layout interleaves coordinators alphabetically and relies on a
legend ("*Coordinators marked with *") that… doesn't render an asterisk on
the card itself. Either split into coord/member rows or add the asterisk
inside `.team-card__name`.

**A11 · Dead CSS rules** — `body.wsite-page-team .team-avatar` (old class
name, replaced by `team-card__avatar`) still styled in every consolidated
body.html.

**A12 · Three different page-title typographies** — Home uses
`<h2> + <font size=6>` in Playfair 34 px; About uses Playfair 48 px centered;
Team uses Raleway 30 px left-aligned dark green. Pick one.

**A13 · 4-colour H2 palette** on consolidated pages — `#156138`,
`rgb(81,81,81)`, `rgb(123,140,137)`, `#42514c` all compete. Lock to
`#1a4d2e` / `#3d8b3d` / `#6b7571`.

**A14 · Interior bulletin interview pages render in a ~60% column** inside a
14-col Weebly table with Gentium justified — worst-readability combo.
Replace with `<article style="max-width:72ch; margin:0 auto">`.

**A15 · pretext-nav-fit.js dynamically imports from esm.sh** — on strict CSP
or blocked CDN this silently falls back to the canvas shim. The canvas
version is fine on its own. Drop the import or self-host pretext.

**A16 · Every page still ships Weebly customer-accounts runtime** — inline
`_W.CustomerAccounts.RPC` + `main-customer-accounts-site.js`. ~35 KB of
third-party JS per pageview with a beacon to Weebly on every load. No
customer/store on this site.

**A17 · `wsite-spacer` divs and `style="height:50px"` noise** — fixed-height
spacers fighting responsive CSS.

### LOW impact

**A18 · Bulletin nav labels on <380px** — all 7 say "Issue n°X"; drop the
"Issue" prefix.

**A19 · Home + About + Membership have three different copies of the
"What is ALIUS" paragraph** — will drift out of sync. Single include via
a partial.

**A20 · `.team-card__coord` CSS exists but no markup uses the class.**

**A21 · `<h2>` used for non-headings** (newsletter label on journal-club,
long descriptive paragraph on membership).

**A22 · Mobile hamburger still Weebly-grey** — not themed in ALIUS green.

**A23 · Every page has `<a href=""><img ... sitename logo></a>`** with an
EMPTY href — clicking reloads the current page. Should be `href="/"`.

---

*First pass written against commit 960a8b0. Agent findings appended
against commit 22570f3. Fixes shipping in subsequent checkpoints.*
