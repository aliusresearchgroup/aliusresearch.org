"""Move the sticky section nav from top to bottom across all consolidated
pages, and upgrade it to a fully responsive, smartphone-friendly, scroll-snap
nav that adapts to any viewport width.

Target files:
  - site-src/content/team/body.html
  - site-src/content/team/original.rewritten.html
  - site-src/content/_consolidated/{bulletin,events,membership}/body.html
  - site-src/content/_consolidated/{bulletin,events,membership}/original.rewritten.html

Changes:
  1. Remove the old top section nav (<ul class="team-section-nav"> or
     <ul class="tab-section-nav">) from the top of each page
  2. Inject a new <nav class="section-nav"> fixed to the bottom of the viewport
     just before </body>
  3. Replace the old CSS block with a new minimalist CSS block that:
       - Renders nav fixed at bottom, full viewport width
       - Uses flex on wide screens, overflow-x scroll-snap on narrow
       - Respects safe-area-inset-bottom (iPhone notches)
       - Adds sufficient bottom padding to the page content so last section
         isn't hidden under the nav

Idempotent: running twice produces the same result.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "site-src" / "content"

# (page_id, relative_dir_under_CONTENT, anchor_list, body_class)
PAGES = [
    ("team", "team", [
        ("Coordinators", "coordinators"),
        ("Research Members", "research-members"),
        ("In Memoriam", "in-memoriam"),
    ], "wsite-page-team"),
    ("bulletin", "_consolidated/bulletin", [
        ("Issue n°7", "bulletin-07"),
        ("Issue n°6", "bulletin-06"),
        ("Issue n°5", "bulletin-05"),
        ("Issue n°4", "bulletin-04"),
        ("Issue n°3", "bulletin-03"),
        ("Issue n°2", "bulletin-02"),
        ("Issue n°1", "bulletin-01"),
    ], "wsite-page-bulletin"),
    ("events", "_consolidated/events", [
        ("ASSC Satellite", "assc-satellite"),
        ("Program", "program"),
        ("Attendees", "attendees"),
        ("Travel", "travel"),
        ("Music", "music"),
    ], "wsite-page-events"),
    ("membership", "_consolidated/membership", [
        ("Active Roles", "active-roles"),
        ("Researcher Membership", "researcher-membership"),
    ], "wsite-page-membership"),
]

STYLE_BLOCK = """<style>
/* Consolidated-page design: minimalist section dividers + fixed bottom nav */
html { scroll-behavior: smooth; }

/* Keep section dividers clean */
body.wsite-page-team .wsite-section-wrap,
body.wsite-page-bulletin .wsite-section-wrap,
body.wsite-page-events .wsite-section-wrap,
body.wsite-page-membership .wsite-section-wrap {
  scroll-margin-top: 16px;
  scroll-margin-bottom: 100px;
}

/* Anchor targets (hidden offset spans sit above dividers) */
.tab-anchor,
.team-anchor {
  position: relative;
  top: -16px;
  visibility: hidden;
  pointer-events: none;
  display: block;
  height: 0;
}

/* Page bottom breathing room so last section isn't hidden under the fixed nav */
body.wsite-page-team #wsite-content,
body.wsite-page-bulletin #wsite-content,
body.wsite-page-events #wsite-content,
body.wsite-page-membership #wsite-content {
  padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
}

/* Fixed bottom section navigation */
.section-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  margin: 0;
  padding: 0.55rem calc(0.75rem + env(safe-area-inset-right, 0px))
           calc(0.55rem + env(safe-area-inset-bottom, 0px))
           calc(0.75rem + env(safe-area-inset-left, 0px));
  background: rgba(249, 249, 249, 0.94);
  backdrop-filter: blur(10px) saturate(1.1);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
  border-top: 1px solid rgba(66, 81, 76, 0.18);
  box-shadow: 0 -6px 18px rgba(0, 0, 0, 0.05);
  -webkit-tap-highlight-color: transparent;
}

.section-nav ol {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-x: auto;
  overflow-y: hidden;
  /* Horizontal scroll snap (browsers that don't support just scroll freely) */
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.section-nav ol::-webkit-scrollbar { display: none; }

.section-nav li {
  flex: 0 0 auto;
  scroll-snap-align: center;
}

.section-nav a {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0.45rem 0.85rem;
  border-radius: 999px;
  color: #42514c;
  text-decoration: none;
  white-space: nowrap;
  font-family: 'Raleway', sans-serif;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  transition: background 160ms ease, color 160ms ease;
  -webkit-touch-callout: none;
  user-select: none;
}
.section-nav a:hover,
.section-nav a:focus,
.section-nav a.is-active {
  background: rgba(123, 140, 137, 0.18);
  color: #2a3330;
  outline: none;
}

/* Narrow-screen tuning */
@media (max-width: 640px) {
  .section-nav { padding-top: 0.45rem; padding-bottom: calc(0.45rem + env(safe-area-inset-bottom, 0px)); }
  .section-nav ol { gap: 0.2rem; justify-content: flex-start; padding: 0 0.25rem; }
  .section-nav a { font-size: 11px; padding: 0.4rem 0.7rem; letter-spacing: 0.06em; }
}
@media (max-width: 380px) {
  .section-nav a { font-size: 10.5px; padding: 0.35rem 0.6rem; }
}

/* Avatar styling (team page) - kept here for a single-source-of-truth */
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
body.wsite-page-team .team-avatar picture {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 25%;
  display: block;
  border-radius: 50%;
  max-width: none !important;
}
@media (max-width: 640px) {
  body.wsite-page-team .team-avatar { width: 140px; height: 140px; }
}

/* Reduce visual noise on section dividers */
body.wsite-page-team .styled-hr,
body.wsite-page-bulletin .styled-hr,
body.wsite-page-events .styled-hr,
body.wsite-page-membership .styled-hr {
  border: 0;
  border-top: 1px solid rgba(66, 81, 76, 0.15);
  max-width: 320px;
  margin: 10px auto 0;
}
</style>
"""


def build_nav_html(anchors: list[tuple[str, str]]) -> str:
    lis = "\n  ".join(
        f'<li><a href="#{anchor}">{title}</a></li>'
        for title, anchor in anchors
    )
    return f"""<nav class="section-nav" aria-label="Section navigation">
  <ol>
  {lis}
  </ol>
</nav>
<script>
(function() {{
  var links = document.querySelectorAll('.section-nav a');
  if (!links.length) return;
  // Highlight active section as user scrolls; snap-center the active link
  var io = new IntersectionObserver(function(entries) {{
    entries.forEach(function(e) {{
      var id = e.target.id;
      if (!id) return;
      var link = document.querySelector('.section-nav a[href="#' + id + '"]');
      if (!link) return;
      if (e.isIntersecting) {{
        links.forEach(function(a) {{ a.classList.remove('is-active'); }});
        link.classList.add('is-active');
        // Snap the active link horizontally into view on narrow screens
        var nav = link.closest('ol');
        if (nav && nav.scrollWidth > nav.clientWidth) {{
          var r = link.getBoundingClientRect(), nr = nav.getBoundingClientRect();
          nav.scrollBy({{
            left: (r.left + r.width / 2) - (nr.left + nr.width / 2),
            behavior: 'smooth'
          }});
        }}
      }}
    }});
  }}, {{ rootMargin: '-40% 0px -40% 0px', threshold: 0 }});
  document.querySelectorAll('[id^="bulletin-"],[id="coordinators"],[id="research-members"],[id="in-memoriam"],[id="assc-satellite"],[id="program"],[id="attendees"],[id="travel"],[id="music"],[id="active-roles"],[id="researcher-membership"]').forEach(function(el) {{ io.observe(el); }});
}})();
</script>"""


# Regex to strip old top nav blocks (both team-section-nav and tab-section-nav styles)
OLD_NAV_RE = re.compile(
    r'<(ul|nav)[^>]*class="(?:team-section-nav|tab-section-nav)[^"]*"[^>]*>.*?</\1>\s*',
    re.DOTALL | re.IGNORECASE,
)

# Strip prior bottom navs (idempotency)
NEW_NAV_RE = re.compile(
    r'<nav[^>]*class="section-nav"[^>]*>.*?</nav>\s*(?:<script>\(function\(\)[^<]*?</script>\s*)?',
    re.DOTALL | re.IGNORECASE,
)

# Strip prior style blocks we injected (detect by a stable marker)
OLD_STYLE_RE = re.compile(
    r'<style>\s*/\* (?:Team page redesign|Main-tab consolidated pages|Consolidated-page design)[^<]*</style>\s*',
    re.DOTALL | re.IGNORECASE,
)


def process_page(path: Path, anchors: list[tuple[str, str]], body_class: str, is_full_doc: bool) -> None:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # Remove prior nav injections (idempotency)
    text = OLD_NAV_RE.sub("", text)
    text = NEW_NAV_RE.sub("", text)
    text = OLD_STYLE_RE.sub("", text)

    # Inject style block
    if is_full_doc and "</head>" in text:
        text = text.replace("</head>", STYLE_BLOCK + "</head>", 1)
    else:
        # Body fragment (body.html) — prepend a <style> block at top so it still applies
        text = STYLE_BLOCK + text

    # Inject new bottom nav: place just before </body> if present, else append
    nav = build_nav_html(anchors)
    if "</body>" in text:
        text = text.replace("</body>", nav + "\n</body>", 1)
    else:
        text = text + "\n" + nav

    path.write_text(text, encoding="utf-8")


def main():
    patterns = [
        ("body.html", False),
        ("original.rewritten.html", True),
        ("original.html", True),
    ]
    for page_id, relpath, anchors, body_class in PAGES:
        base = CONTENT / relpath
        for fname, is_full in patterns:
            path = base / fname
            if not path.exists():
                continue
            process_page(path, anchors, body_class, is_full)
            print(f"Updated: {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
