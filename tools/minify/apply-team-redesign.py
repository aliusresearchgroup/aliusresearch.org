"""Rewrite /team/ page to use uniform circular face-cropped portraits and
add a sticky section nav + smooth scroll.

Edits:
- site-src/content/team/body.html
- site-src/content/team/original.rewritten.html

For each <img> that refers to an image in /media/images/ or /uploads/ (any
portrait), replaces src with the face-cropped /media/team-portraits/<slug>.jpg
version and wraps it in a <div class="team-avatar"> for CSS circle styling.

Injects a <style> block and section-nav <ul> into the page.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEAM_DIR = REPO / "site-src" / "content" / "team"

BODY_PATH = TEAM_DIR / "body.html"
REWRITTEN_PATH = TEAM_DIR / "original.rewritten.html"


def slugify(path: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    return s[:80]


STYLE_BLOCK = """<style>
/* Team page redesign: circular avatars + sticky section nav + smooth scroll */
html { scroll-behavior: smooth; }
body.wsite-page-team .team-section-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  padding: 0.9rem 1rem;
  margin: 0;
  list-style: none;
  background: rgba(249, 249, 249, 0.96);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-bottom: 1px solid rgba(66, 81, 76, 0.18);
  font-family: 'Raleway', sans-serif;
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
body.wsite-page-team .team-section-nav a {
  color: #42514c;
  text-decoration: none;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  transition: background 160ms ease, color 160ms ease;
}
body.wsite-page-team .team-section-nav a:hover,
body.wsite-page-team .team-section-nav a:focus {
  background: rgba(123, 140, 137, 0.15);
  color: #2a3330;
}
body.wsite-page-team .team-anchor {
  position: relative;
  top: -72px;
  visibility: hidden;
  pointer-events: none;
}
body.wsite-page-team .team-avatar {
  width: 180px;
  height: 180px;
  margin: 0 auto 0.8rem;
  border-radius: 50%;
  overflow: hidden;
  background: #e8ece9;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}
body.wsite-page-team .team-avatar img,
body.wsite-page-team .team-avatar picture,
body.wsite-page-team .team-avatar source {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  display: block;
  border-radius: 50%;
  max-width: none !important;
}
body.wsite-page-team .wsite-section-wrap { scroll-margin-top: 80px; }
body.wsite-page-team .wsite-multicol-col:first-child {
  text-align: center;
  vertical-align: middle !important;
}
body.wsite-page-team .wsite-image {
  text-align: center !important;
  padding: 0 !important;
  margin: 0 auto !important;
}
@media (max-width: 640px) {
  body.wsite-page-team .team-section-nav {
    flex-wrap: wrap;
    gap: 0.6rem;
    font-size: 11px;
    padding: 0.6rem 0.5rem;
  }
  body.wsite-page-team .team-avatar { width: 140px; height: 140px; }
}
</style>
"""

NAV_BLOCK = """<ul class="team-section-nav">
  <li><a href="#coordinators">Coordinators</a></li>
  <li><a href="#research-members">Research Members</a></li>
  <li><a href="#in-memoriam">In Memoriam</a></li>
</ul>
"""

ANCHOR_MAP = {
    "Coordinators": "coordinators",
    "Research Members": "research-members",
    "In Memoriam: Martin Fortier": "in-memoriam",
}


def rewrite_img_tags(html: str) -> str:
    """Replace <img src="/media/images/X.jpg" ...> (in team sections) with
    <div class="team-avatar"><img src="/media/team-portraits/<slug>.jpg" ...></div>.

    Only applies to images inside a .wsite-multicol-col (portrait columns)
    and skips the ALIUS logo, background images, and the Martin Fortier portrait
    (which has a text-only section).
    """
    def repl(m: re.Match) -> str:
        whole = m.group(0)
        src_match = re.search(r'src="([^"]+)"', whole)
        if not src_match:
            return whole
        src = src_match.group(1)
        # Skip non-portrait images
        if any(x in src for x in ("1477332210.png", "background-images", "/logo")):
            return whole
        # Only rewrite if it's a media path (images / uploads)
        if not (src.lstrip("/").startswith("media/images/") or "uploads/" in src):
            return whole
        slug = slugify(src)
        new_src = f"/media/team-portraits/{slug}.jpg"
        new_webp = f"/media/team-portraits/{slug}.webp"
        # Strip width/height/style constraints that'd interfere with object-fit
        cleaned = re.sub(r'\s(width|height|style)="[^"]*"', "", whole)
        cleaned = re.sub(r'src="[^"]+"', f'src="{new_src}"', cleaned)
        return (
            '<div class="team-avatar">'
            f'<picture><source srcset="{new_webp}" type="image/webp">{cleaned}</picture>'
            '</div>'
        )

    return re.sub(r"<img[^>]+>", repl, html)


def unwrap_existing_picture(html: str) -> str:
    """Remove the build's <picture> wrapping so we can re-wrap with team crops.

    The build's wrap-images-in-picture.py adds <picture><source ...><img></picture>
    around <img>. When we edit original.rewritten.html manually, we want the raw
    <img> so our rewrite_img_tags() produces clean output; post-build will wrap again.
    """
    # Unwrap <picture><source ...><img ...></picture> → <img ...>
    return re.sub(
        r'<picture>\s*<source[^>]+>\s*(<img[^>]+>)\s*</picture>',
        r'\1',
        html,
    )


def inject_style_and_nav(html: str) -> str:
    """Inject CSS into <head> and section nav at top of wsite-content."""
    # Inject style block before </head> if not already present
    if "team-section-nav" not in html:
        html = html.replace("</head>", STYLE_BLOCK + "</head>", 1)
    # Inject nav right after <div id="wsite-content"...> opening
    html = re.sub(
        r'(<div\s+id="wsite-content"[^>]*>)',
        r'\1\n' + NAV_BLOCK,
        html,
        count=1,
    )
    return html


def insert_anchors_before_dividers(html: str) -> str:
    """Insert <span id="coordinators"> anchors before each section divider heading."""
    for title, anchor in ANCHOR_MAP.items():
        # Find the section-wrap containing this title header; insert an anchor span
        # just before the section-wrap div.
        pattern = re.compile(
            r'(<div class="wsite-section-wrap">\s*<div class="wsite-section wsite-body-section wsite-custom-background">\s*<div class="wsite-section-content">\s*<div class="container">\s*<div class="wsite-section-elements">\s*<h2 class="wsite-content-title"[^>]*>\s*<strong[^>]*>\s*<font[^>]*>)'
            + re.escape(title)
            + r'(</font>)',
            re.IGNORECASE,
        )
        anchor_html = f'<span id="{anchor}" class="team-anchor"></span>'
        # Simpler approach: prepend anchor before the section-wrap that CONTAINS the title
        # Use a looser pattern: match the section-wrap opening, then search within for title
        pass

    # Simpler idempotent approach: after each wsite-section-wrap with title containing
    # our trigger, prepend anchor span.
    out: list[str] = []
    idx = 0
    for title, anchor in ANCHOR_MAP.items():
        pat = re.compile(r'(<div class="wsite-section-wrap">(?:(?!</h2>).)*?>' + re.escape(title) + r')', re.DOTALL)
        m = pat.search(html)
        if not m:
            continue
        start = m.start()
        anchor_html = f'<span id="{anchor}" class="team-anchor"></span>\n'
        # Avoid double-insertion
        if f'id="{anchor}"' in html:
            continue
        html = html[:start] + anchor_html + html[start:]
    return html


def process(path: Path, include_style: bool) -> None:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    text = unwrap_existing_picture(text)
    text = rewrite_img_tags(text)
    text = insert_anchors_before_dividers(text)
    if include_style:
        text = inject_style_and_nav(text)
    path.write_text(text, encoding="utf-8")
    print(f"Updated: {path.relative_to(REPO)}")


def main():
    # For body.html the <head> is NOT in this file; still inject nav
    process(BODY_PATH, include_style=False)
    process(REWRITTEN_PATH, include_style=True)


if __name__ == "__main__":
    main()
