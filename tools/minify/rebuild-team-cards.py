"""Rebuild /team/ with a normal card grid (Uncodixify aesthetic).

Each member becomes a simple card with:
  - Photo (circular avatar, top)
  - Name (h3, bold but not oversized)
  - Affiliation/role (small muted line, optional)
  - Bio paragraph (normal body text)
  - Icon row with links (LinkedIn, ResearchGate, Scholar, site, email)

Uncodixify principles applied:
  - Border radius 8-10px (not 20px)
  - 1px solid subtle border, subtle shadow only
  - System-like spacing (16/24px)
  - No gradients, no glass, no floating panels
  - Avatars are 88px normal circles (not 180px dramatic)
  - Monochrome icons at 18px, subtle hover
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
TEAM_DIR = REPO / "site-src" / "content" / "team"

SHELL_REWRITTEN = REPO / "site-src" / "content" / "about" / "team" / "team-222796" / "original.rewritten.html"
SHELL_BODY = REPO / "site-src" / "content" / "about" / "team" / "team-222796" / "body.html"
SHELL_ORIG = REPO / "site-src" / "content" / "about" / "team" / "team-222796" / "original.html"

SOURCES = [
    ("Coordinators", "coordinators",        REPO / "site-src" / "content" / "about" / "team" / "team-222796"),
    ("Research Members", "research-members", REPO / "site-src" / "content" / "about" / "team" / "team-955042"),
    ("In Memoriam", "in-memoriam",          REPO / "site-src" / "content" / "pages" / "martinfortier"),
]

# ---- helpers ----

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def extract_content(body: str) -> str:
    m = re.search(r'<div\s+id="wsite-content"[^>]*>(.*?)(?=</div>\s*</div>\s*<div\s+id="footer")', body, re.DOTALL)
    if not m:
        raise RuntimeError("no wsite-content")
    return m.group(1)


def extract_wraps(text: str) -> list[str]:
    sections = []
    idx = 0
    while True:
        start = text.find('<div class="wsite-section-wrap">', idx)
        if start == -1:
            break
        depth = 0
        i = start
        while i < len(text):
            no = text.find('<div', i + 1)
            nc = text.find('</div>', i + 1)
            if nc == -1:
                break
            if no != -1 and no < nc:
                depth += 1
                i = no
            else:
                if depth == 0:
                    end = nc + 6
                    sections.append(text[start:end])
                    idx = end
                    break
                depth -= 1
                i = nc
        else:
            break
    return sections


def strip_zero_width(s: str) -> str:
    return s.replace("​", "").replace("&#8203;", "").replace("&#x200B;", "").strip()


def html_to_plain(s: str) -> str:
    """HTML → plain text, collapsing whitespace."""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    import html as _html
    s = _html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_member(wrap: str) -> dict | None:
    # Skip the "Honorary members" divider and any section without a multicol.
    if "wsite-multicol" not in wrap:
        return None

    img_m = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', wrap)
    image = img_m.group(1) if img_m else None

    # Find the main paragraph block (the bio). It's the largest .paragraph div.
    paragraphs = re.findall(r'<div class="paragraph"[^>]*>(.*?)</div>', wrap, re.DOTALL)
    bio_html = max(paragraphs, key=len) if paragraphs else ""
    bio_plain = html_to_plain(bio_html)

    # Name heuristics: look for the first sizable bold/font chunk in the bio.
    name = None
    candidates = []
    for m in re.finditer(
        r'<font[^>]*size="[45]"[^>]*>(?:\s|<[^>]+>)*?([^<]{2,80}?)(?:\s|<[^>]+>)*?</font>',
        bio_html,
    ):
        candidates.append(strip_zero_width(m.group(1)))
    if not candidates:
        for m in re.finditer(r'<strong[^>]*>(?:\s|<[^>]+>)*?([^<]{2,80}?)(?:\s|<[^>]+>)*?</strong>', bio_html):
            candidates.append(strip_zero_width(m.group(1)))
    # Pick first meaningful candidate (not "CV" etc.)
    for c in candidates:
        if c and c.lower() not in ("cv", "picture", "image"):
            name = c
            break
    if not name:
        # Fallback: first word pair of bio
        words = bio_plain.split()
        name = " ".join(words[:2]) if words else "Team Member"

    # Remove name + its immediate following email/role line from bio so the card
    # doesn't repeat the name in the body. Cut bio at first paragraph boundary.
    bio_trimmed = bio_plain
    if name and name in bio_trimmed:
        bio_trimmed = bio_trimmed.split(name, 1)[-1].strip()
    # Drop leading "(CV)" markers
    bio_trimmed = re.sub(r'^\s*\([^)]*CV[^)]*\)\s*', '', bio_trimmed, flags=re.IGNORECASE)
    bio_trimmed = bio_trimmed.strip(" :-—")

    # Extract links (href + text) from the whole wrap
    raw_links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', wrap, re.DOTALL)
    links: list[dict] = []
    seen_href = set()
    for href, text in raw_links:
        text_plain = html_to_plain(text)
        if text_plain.lower() in ("picture", "image"):
            continue
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        if href.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf")):
            # CV PDF stays — classify separately below
            pass
        if href in seen_href:
            continue
        seen_href.add(href)
        links.append({"href": href, "text": text_plain})

    # Extract email (first mailto or obfuscated pattern)
    email_m = re.search(r'<em[^>]*>([^<]*\[at\][^<]*\[dot\][^<]*)</em>', bio_html) or \
              re.search(r'([\w._-]+)\s*\[at\]\s*([\w.-]+)\s*\[dot\]\s*(\w+)', bio_plain)
    email = None
    if email_m:
        txt = email_m.group(0)
        m2 = re.search(r'([\w._-]+)\s*\[at\]\s*([\w.-]+)\s*\[dot\]\s*(\w+)', txt) or re.search(r'([\w._-]+)\s*\[at\]\s*([\w.-]+)\s*\[dot\]\s*(\w+)', bio_plain)
        if m2:
            email = f"{m2.group(1)}@{m2.group(2)}.{m2.group(3)}"
    if email and email in bio_trimmed:
        bio_trimmed = bio_trimmed.replace(email, "").strip()
        # Also remove "[at] ... [dot] ..." style
    bio_trimmed = re.sub(r'[\w._-]+\s*\[at\]\s*[\w.-]+\s*\[dot\]\s*\w+', '', bio_trimmed).strip()

    return {
        "image": image,
        "name": strip_zero_width(name),
        "bio": bio_trimmed[:650].strip(),
        "links": links,
        "email": email,
    }


# ---- link classification into icon types ----

ICON_DEFS = {
    "linkedin":    ("LinkedIn",       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>'),
    "researchgate":("ResearchGate",   '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 5h3v14H7zM14 5h3v14h-3zM7 11h10v2H7z"/></svg>'),
    "scholar":     ("Google Scholar", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>'),
    "academia":    ("Academia",       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5V4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>'),
    "orcid":       ("ORCID",          '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><text x="12" y="16" text-anchor="middle" font-size="10" font-weight="bold">iD</text></svg>'),
    "twitter":     ("Twitter / X",    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 3H22l-7.5 8.6L23 21h-6.8l-5.3-6.9L4.8 21H1.7l8-9.2L1 3h7l4.8 6.3zM17.7 19.2h1.9L6.4 4.7H4.3z"/></svg>'),
    "github":      ("GitHub",         '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.9 10.9c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.5-.3-5.2-1.3-5.2-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5z"/></svg>'),
    "site":        ("Website",        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15 15 0 0 1 4 10 15 15 0 0 1-4 10 15 15 0 0 1-4-10 15 15 0 0 1 4-10z"/></svg>'),
    "email":       ("Email",          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>'),
    "pdf":         ("CV (PDF)",       '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/></svg>'),
}

def classify_link(href: str) -> str:
    try:
        host = urlparse(href).netloc.lower().replace("www.", "")
    except Exception:
        return "site"
    if "linkedin.com" in host: return "linkedin"
    if "researchgate.net" in host: return "researchgate"
    if "scholar.google" in host: return "scholar"
    if "academia.edu" in host: return "academia"
    if "orcid.org" in host: return "orcid"
    if "twitter.com" in host or host == "x.com" or host.endswith(".x.com"): return "twitter"
    if "github.com" in host: return "github"
    if href.lower().endswith(".pdf"): return "pdf"
    return "site"


# ---- card rendering ----

def render_card(m: dict) -> str:
    img = m.get("image") or ""
    name = m.get("name") or ""
    bio = m.get("bio") or ""
    # Group links by icon type; keep only one per type (dedupe)
    link_by_type: dict[str, str] = {}
    for l in m.get("links") or []:
        t = classify_link(l["href"])
        link_by_type.setdefault(t, l["href"])
    if m.get("email"):
        link_by_type.setdefault("email", f'mailto:{m["email"]}')

    icons_html = ""
    # Preferred order
    for key in ("linkedin", "twitter", "scholar", "researchgate", "orcid", "academia", "github", "site", "pdf", "email"):
        if key in link_by_type:
            label, svg = ICON_DEFS[key]
            href = link_by_type[key]
            target = '' if href.startswith('mailto:') else ' target="_blank" rel="noopener"'
            icons_html += (
                f'<a class="team-card__icon" href="{href}" aria-label="{label}"{target}>{svg}</a>'
            )

    img_html = ''
    if img:
        img_html = f'<div class="team-card__avatar"><img src="{img}" alt="{name}" loading="lazy" decoding="async"></div>'

    return f'''<article class="team-card">
  {img_html}
  <h3 class="team-card__name">{name}</h3>
  <p class="team-card__bio">{bio}</p>
  <div class="team-card__links">{icons_html}</div>
</article>'''


CSS = """<style>
/* Team page — normal card grid, uniform typography (Uncodixify aesthetic) */

body.wsite-page-team #wsite-content {
  padding-bottom: calc(100px + env(safe-area-inset-bottom, 0px));
}

/* One font stack for the entire page: Raleway, with system-font fallback */
body.wsite-page-team,
body.wsite-page-team .team-page-title h1,
body.wsite-page-team .team-section-heading h2,
body.wsite-page-team .team-card,
body.wsite-page-team .team-card__name,
body.wsite-page-team .team-card__bio,
body.wsite-page-team .team-card__links a {
  font-family: 'Raleway', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Page title */
body.wsite-page-team .team-page-title {
  max-width: 1200px;
  margin: 48px auto 0;
  padding: 0 24px;
}
body.wsite-page-team .team-page-title h1 {
  font-size: 28px !important;
  font-weight: 600 !important;
  margin: 0 !important;
  color: #1f2826 !important;
  letter-spacing: -0.01em !important;
  text-transform: none !important;
  text-align: left !important;
}
body.wsite-page-team .team-page-title p {
  margin: 6px 0 0 !important;
  color: #6b7571 !important;
  font-size: 14px !important;
  line-height: 1.5 !important;
  font-weight: 400 !important;
}

/* Section break (Coordinators / Research Members / In Memoriam) */
body.wsite-page-team .team-section-heading {
  max-width: 1200px;
  margin: 56px auto 0;
  padding: 0 24px 14px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
body.wsite-page-team .team-section-heading h2 {
  font-size: 18px !important;
  font-weight: 600 !important;
  margin: 0 !important;
  color: #2a3330 !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  text-align: left !important;
}

/* Grid */
body.wsite-page-team .team-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

/* Card */
body.wsite-page-team .team-card {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
body.wsite-page-team .team-card:hover {
  border-color: rgba(0, 0, 0, 0.18);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

body.wsite-page-team .team-card__avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  background: #f2f4f3;
  margin-bottom: 14px;
}
body.wsite-page-team .team-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 25%;
  display: block;
  max-width: none !important;
  border-radius: 50%;
}

body.wsite-page-team .team-card__name {
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #1f2826 !important;
  margin: 0 0 8px !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  line-height: 1.3 !important;
}

body.wsite-page-team .team-card__bio {
  font-size: 13px !important;
  line-height: 1.5 !important;
  color: #4a5350 !important;
  margin: 0 0 14px !important;
  font-weight: 400 !important;
  flex: 1;
  /* Clamp to 6 lines with ellipsis for consistent card heights */
  display: -webkit-box;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-align: left;
  width: 100%;
}

body.wsite-page-team .team-card__links {
  display: flex;
  gap: 2px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: auto;
  padding-top: 4px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  width: 100%;
}
body.wsite-page-team .team-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 4px;
  color: #6b7571;
  transition: color 120ms ease, background 120ms ease;
}
body.wsite-page-team .team-card__icon:hover,
body.wsite-page-team .team-card__icon:focus-visible {
  color: #1f2826;
  background: rgba(0, 0, 0, 0.04);
  outline: none;
}
body.wsite-page-team .team-card__icon svg {
  width: 16px;
  height: 16px;
}

@media (max-width: 640px) {
  body.wsite-page-team .team-page-title { margin-top: 32px; padding: 0 16px; }
  body.wsite-page-team .team-page-title h1 { font-size: 24px !important; }
  body.wsite-page-team .team-section-heading { margin-top: 40px; padding: 0 16px 12px; }
  body.wsite-page-team .team-grid { padding: 16px; gap: 12px; }
}
@media (max-width: 420px) {
  body.wsite-page-team .team-grid { grid-template-columns: 1fr; }
  body.wsite-page-team .team-card { padding: 18px; }
}

/* Hide the original Weebly section-wraps on this page — the grid is our render path */
body.wsite-page-team #wsite-content > .wsite-section-wrap { display: none !important; }
body.wsite-page-team #wsite-content .wsite-background,
body.wsite-page-team #wsite-content .wsite-custom-background { background: transparent !important; }
</style>
"""


def parse_source(source_dir: Path, mode: str = "members") -> list[dict]:
    """mode='members' extracts one card per section-wrap; mode='single' merges
    all content into a single card (used for the Martin Fortier tribute)."""
    body = read(source_dir / "original.rewritten.html")
    content = extract_content(body)
    wraps = extract_wraps(content)

    if mode == "single":
        # Merge all wraps into one card. Use the first image and combined bio.
        combined_html = "\n".join(wraps)
        img_m = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', combined_html)
        image = img_m.group(1) if img_m else None
        paragraphs = re.findall(r'<div class="paragraph"[^>]*>(.*?)</div>', combined_html, re.DOTALL)
        bio_plain = html_to_plain("\n".join(paragraphs))
        # Collect all external links
        raw_links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', combined_html, re.DOTALL)
        links = []
        seen = set()
        for href, text in raw_links:
            text_plain = html_to_plain(text)
            if text_plain.lower() in ("picture", "image"):
                continue
            if href.startswith("#") or href in seen:
                continue
            seen.add(href)
            links.append({"href": href, "text": text_plain})
        return [{
            "image": image,
            "name": "Martin Fortier",
            "bio": bio_plain[:900].strip(),
            "links": links,
            "email": None,
        }]

    out = []
    for w in wraps:
        m = parse_member(w)
        if not m or not m.get("name"):
            continue
        # Skip section-title-only cards
        low = m.get("name", "").lower()
        if low in ("the alius research team",):
            continue
        # Skip cards with no image AND short/empty bio (likely testimonials or section notes)
        if not m.get("image") and len(m.get("bio", "")) < 60:
            continue
        # Drop obvious parse failures (name is a sentence fragment)
        if len(m.get("name", "")) > 50 or m.get("name") == "Team Member":
            # Try to rescue: if we have an image and some bio, use filename stem as fallback
            if m.get("image") and m.get("bio"):
                stem = Path(urlparse(m["image"]).path).stem
                stem = re.sub(r'[-_]\d+$', '', stem)  # strip trailing numbers
                m["name"] = stem.replace("-", " ").title()
            else:
                continue
        out.append(m)
    return out


def _assemble(shell_text: str, content_html: str) -> str:
    m = re.search(
        r'(<div\s+id="wsite-content"[^>]*>).*?(</div>\s*</div>\s*<div\s+id="footer")',
        shell_text,
        flags=re.DOTALL,
    )
    if not m:
        raise RuntimeError("no wsite-content in shell")
    pre = shell_text[:m.start()]
    open_tag = m.group(1)
    post = shell_text[m.start(2):]
    out = pre + open_tag + "\n" + content_html + "\n" + post
    out = re.sub(r"<title>[^<]*</title>", "<title>Team - Alius</title>", out, count=1)
    out = out.replace("wsite-page-team-222796", "wsite-page-team")
    return out


def build_content() -> str:
    parts: list[str] = []
    parts.append(CSS)
    parts.append('<div class="team-page-title"><h1>The ALIUS Team</h1><p>Coordinators, research members, and colleagues in memoriam.</p></div>')
    seen_names: set[str] = set()
    for label, anchor, source_dir in SOURCES:
        mode = "single" if anchor == "in-memoriam" else "members"
        members = parse_source(source_dir, mode=mode)
        if not members:
            continue
        # Dedupe by normalized name — a person listed as both Coordinator and
        # Research Member only renders in the first section they appear in.
        deduped = []
        for m in members:
            key = re.sub(r"[^a-z0-9]+", "", (m.get("name") or "").lower())
            if not key or key in seen_names:
                continue
            seen_names.add(key)
            deduped.append(m)
        if not deduped:
            continue
        parts.append(f'<span id="{anchor}" class="team-anchor"></span>')
        parts.append(f'<div class="team-section-heading"><h2>{label}</h2></div>')
        parts.append('<div class="team-grid">')
        for m in deduped:
            parts.append(render_card(m))
        parts.append('</div>')
    return "\n".join(parts)


def main():
    content_html = build_content()
    for fname, shell_path in [
        ("body.html", SHELL_BODY),
        ("original.rewritten.html", SHELL_REWRITTEN),
        ("original.html", SHELL_ORIG),
    ]:
        shell = read(shell_path)
        out = _assemble(shell, content_html)
        (TEAM_DIR / fname).write_text(out, encoding="utf-8")
        print(f"  wrote {fname}")

if __name__ == "__main__":
    main()
