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

# Members whose profile data lives on other pages — curated manually to
# guarantee accurate name/bio/image.
EXTRA_MEMBERS = [
    {
        "name": "Paweł Motyka",
        "image": "/media/images/pawel-4.png",
        "bio": (
            "Dr. Paweł Motyka is a researcher in psychology specializing in "
            "consciousness studies, altered states of consciousness, and "
            "multisensory integration. He is currently affiliated with the "
            "Institute of Psychology at the Polish Academy of Sciences. His "
            "research explores the interplay between interoception and "
            "exteroception, time perception, and the role of bodily processes "
            "in conscious awareness."
        ),
        "links": [
            {"href": "https://scholar.google.com/citations?user=gKMKYegAAAAJ", "text": "Google Scholar"},
        ],
        "email": None,
    },
    {
        "name": "France Lerner",
        "image": "/media/images/france-lerner.png",
        "bio": (
            "France Lerner is an interdisciplinary artist and researcher at "
            "the intersection of neuroaesthetics, consciousness studies, and "
            "immersive technologies. She received her PhD in Art and Science "
            "from the Royal Academy of Arts and the Université de Liège, "
            "in collaboration with the Coma Science Group under Prof. Steven "
            "Laureys. Following postdoctoral research at the Weizmann Institute "
            "of Science (Laboratory for Robotics and Virtual Reality) and an "
            "Assistant Professorship at BIMSA in Beijing, she is currently "
            "Research Fellow at the University of Haifa in the laboratory of "
            "Aviva Berkovitch-Ohana. Her work investigates the spatial and "
            "perceptual organization of Near-Death Experiences — developing "
            "visual methodologies that combine participant drawings, "
            "neurophenomenological analysis, and generative AI to reconstruct "
            "subjective experiences across altered states of consciousness."
        ),
        "links": [],
        "email": None,
    },
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
    # Strip obfuscated "user [at] sub.sub.domain [dot] tld" — allow dots
    # inside domain labels AND multiple [dot] pieces in the domain.
    bio_trimmed = re.sub(
        r'[\w.+\-]+\s*\[at\]\s*(?:[\w.\-]+\s*\[dot\]\s*)+[\w.\-]+',
        '',
        bio_trimmed,
    ).strip()
    # Also plain "user@host.tld" addresses that leaked through as literal text
    bio_trimmed = re.sub(r'\b[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}\b', '', bio_trimmed).strip()
    # Catch orphan fragments left when a leading mailto> text got stripped but
    # its visible partial remained (e.g. "neuro [dot] ", "ac [dot] il").
    # Remove any leading "<word> [dot] [<word> [dot] ...]" at the START of the
    # bio until the first capitalised sentence word, but keep sensible content.
    bio_trimmed = re.sub(
        r'^\s*(?:[\w\-]+\s*\[(?:at|dot)\]\s*)+',
        '',
        bio_trimmed,
    ).strip()
    # Remove any dangling " [dot] <tld>" that may still lead the bio
    bio_trimmed = re.sub(r'^\s*\[dot\]\s*\w+\s*', '', bio_trimmed).strip()
    # Remove lone punctuation / empty-bracket leftovers
    bio_trimmed = re.sub(r'^[\s,.;:\-—–()]+', '', bio_trimmed).strip()

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

def slug_name(name: str) -> str:
    import html as _html
    plain = _html.unescape(re.sub(r"<[^>]+>", "", name or ""))
    s = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    return f"member-{s}" if s else "member"


def obfuscate_email(email: str) -> str:
    """Produce 'user [at] domain [dot] tld' form for scraper-hostile display."""
    if "@" not in email:
        return email
    user, _, rest = email.partition("@")
    parts = rest.split(".")
    return f"{user} [at] {'.'.join(parts[:-1]) if len(parts) > 1 else rest} [dot] {parts[-1] if len(parts) > 1 else ''}".strip()


def render_card(m: dict, is_coordinator: bool = False) -> str:
    img = m.get("image") or ""
    name = m.get("name") or ""
    bio = m.get("bio") or ""
    slug = slug_name(name)
    # Group links by icon type; keep only one per type (dedupe)
    link_by_type: dict[str, str] = {}
    for l in m.get("links") or []:
        t = classify_link(l["href"])
        link_by_type.setdefault(t, l["href"])

    icons_html = ""
    for key in ("linkedin", "twitter", "scholar", "researchgate", "orcid", "academia", "github", "site", "pdf"):
        if key in link_by_type:
            label, svg = ICON_DEFS[key]
            href = link_by_type[key]
            icons_html += (
                f'<a class="team-card__icon team-card__icon--{key}" href="{href}" '
                f'aria-label="{label}" title="{label}" target="_blank" rel="noopener">{svg}</a>'
            )

    # Email: no mailto — render as a hoverable badge that reveals the obfuscated
    # address via a CSS tooltip, so scrapers don't get a raw address.
    if m.get("email"):
        _, svg = ICON_DEFS["email"]
        obf = obfuscate_email(m["email"])
        icons_html += (
            f'<span class="team-card__icon team-card__icon--email" '
            f'role="button" tabindex="0" aria-label="Email" '
            f'data-email="{obf}" title="{obf}">{svg}'
            f'<span class="team-card__email-tooltip">{obf}</span></span>'
        )

    img_html = ''
    if img:
        img_html = f'<div class="team-card__avatar"><img src="{img}" alt="{name}" loading="lazy" decoding="async"></div>'

    coord_class = ' team-card--coord' if is_coordinator else ''
    role_html = (
        '<p class="team-card__role">Team Coordinator</p>'
        if is_coordinator else
        '<p class="team-card__role team-card__role--muted">Research Member</p>'
    )
    return f'''<article class="team-card{coord_class}" id="{slug}">
  {img_html}
  <h3 class="team-card__name">{name}</h3>
  {role_html}
  <p class="team-card__bio">{bio}</p>
  <div class="team-card__links">{icons_html}</div>
</article>'''


def render_memoriam(m: dict) -> str:
    """Full-width dedicated In Memoriam section for Martin Fortier at the
    bottom of /team/. Pulls from the original tribute text to give him
    a proper page-sized memorial rather than a single card.
    """
    img = m.get("image") or ""

    return f'''<section class="memoriam" id="martinfortier" aria-labelledby="memoriam-heading">
  <div class="memoriam__divider"></div>
  <p class="memoriam__eyebrow">In Memoriam</p>
  <h2 class="memoriam__name" id="memoriam-heading">Martin Fortier</h2>
  <p class="memoriam__role">Co-Founder of ALIUS (2016) · 1990–2020</p>

  <div class="memoriam__hero">
    <div class="memoriam__photo"><img src="{img}" alt="Martin Fortier" loading="lazy" decoding="async"></div>
    <div class="memoriam__lede">
      <p>On April 11th, 2020, Martin Fortier tragically passed away after a long and harrowing battle with cancer. He was thirty years old. We mourn the loss of a wonderful friend and a brilliant colleague, gone far too soon to realize his extraordinary potential despite his many precocious achievements.</p>
      <p><a class="memoriam__primary" href="/bulletin/interviews/bulletin04-martintribute/">Read ALIUS' full scientific tribute to the work of Martin Fortier →</a></p>
    </div>
  </div>

  <div class="memoriam__col">
    <h3 class="memoriam__subhead">The Neuroanthropology of Hallucinogenic Experiences</h3>
    <p>Martin's research sat at the intersection of philosophy of mind, cognitive anthropology and the cognitive science of religion. He argued that the phenomenology of so-called psychedelic states could not be understood through nativist neuropharmacology alone and that cultural priors, ritual context, expectation and attentional scaffolding shaped the experience in deep and tractable ways. His preferred term was <em>serotonergic hallucinogen</em> rather than "psychedelic" — a deliberately non-commital label designed to keep experimental work free of 20th-century counter-cultural framing.</p>
    <p>He developed a dimensional model of altered states organized around attention, somatosensory integration and cultural priors, and he was a relentless reader — capable of synthesising neuroscience, Tibetan Buddhist phenomenology, cognitive science of religion and French-tradition philosophy of mind in a single argument. He believed ALIUS should be a space where philosophers, anthropologists and neuroscientists argued with each other as peers.</p>
  </div>

  <div class="memoriam__col">
    <h3 class="memoriam__subhead">Bulletin interviews co-edited by Martin</h3>
    <p>Martin co-founded and edited the ALIUS Bulletin, leading many of its landmark interviews. A selection of his contributions:</p>
    <ul class="memoriam__works">
      <li>Tanya Luhrmann — <em>The anthropology of mind: exploring unusual sensations and spiritual experiences across cultures</em>.</li>
      <li>Robin Carhart-Harris — <em>Consciousness and psychedelics</em> (with Raphaël Millière).</li>
      <li>Karl Friston — <em>Of woodlice and men: a Bayesian account of cognition, life and consciousness</em> (with Daniel A. Friedman).</li>
      <li>Karl Friston — <em>Am I autistic? An intellectual autobiography</em>.</li>
      <li>Ann Taves — <em>Conceptual, anthropological and cognitive issues surrounding religious experience</em> (with Maddalena Canna).</li>
    </ul>
  </div>

  <div class="memoriam__col memoriam__tribute">
    <h3 class="memoriam__subhead">A personal tribute</h3>
    <blockquote>
      <p>It is with grief and sorrow that I share this post, in remembrance of Martin Fortier — one of the dearest friends and contributors within our scientific community. His passing came too soon and will have left a deep absence in our hearts. I derived a deep sense of belonging to the academic community by knowing Martin, and rarely have I encountered somebody so generous with his knowledge, so willing to collaborate across disciplines, so dedicated to a vision of science as a societal project.</p>
      <p>Martin's openness to collaborate with other people served as a role model to value science as a societal project — in contrast to the publish-or-perish mentality ripe with instances of appropriation and intellectual territoriality. He sought out conversations; he disagreed well; he left every room more curious than he found it.</p>
      <footer>— George Fejer, on behalf of ALIUS</footer>
    </blockquote>
  </div>
</section>'''


def render_bottom_names_nav(members: list[dict], coord_keys: set[str]) -> str:
    """Fixed-bottom alphabetical names nav. Horizontally scrolls on narrow
    viewports (scroll-snap applies via .section-nav CSS already in use)."""
    items = []
    for m in members:
        name = m.get("name") or ""
        slug = slug_name(name)
        key = re.sub(r"[^a-z0-9]+", "", name.lower())
        mark = ' *' if key in coord_keys else ''
        items.append(f'<li><a href="#{slug}">{name}{mark}</a></li>')
    items_html = "\n  ".join(items)
    return f'''<nav class="section-nav team-names-nav" aria-label="All team members">
  <ol>
  {items_html}
  </ol>
</nav>
<script src="/assets/js/pretext-nav-fit.js" defer></script>'''


def render_names_index(all_members: list[tuple[str, dict]]) -> str:
    """Render an alphabetical, multi-column clickable index.

    all_members is a list of (section, member) tuples so we know who's a
    coordinator. Coordinators get a trailing asterisk.
    """
    coord_keys = {
        re.sub(r"[^a-z0-9]+", "", (m.get("name") or "").lower())
        for section, m in all_members if section == "Coordinators"
    }
    unique: list[dict] = []
    seen = set()
    for _section, m in all_members:
        key = re.sub(r"[^a-z0-9]+", "", (m.get("name") or "").lower())
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(m)
    # Sort by family name (last word, case-insensitive) then first name
    def sort_key(m):
        import html as _html
        name = _html.unescape(re.sub(r"<[^>]+>", "", m.get("name") or ""))
        parts = name.strip().split()
        return (parts[-1].lower() if parts else "", name.lower())
    unique.sort(key=sort_key)
    items = []
    for m in unique:
        name = m.get("name") or ""
        slug = slug_name(name)
        key = re.sub(r"[^a-z0-9]+", "", name.lower())
        star = " *" if key in coord_keys else ""
        items.append(f'<li><a href="#{slug}">{name}{star}</a></li>')
    items_html = "\n    ".join(items)
    return f'''<nav class="team-index" aria-label="Team members">
  <p class="team-index__legend">* Team Coordinators</p>
  <ol class="team-index__list">
    {items_html}
  </ol>
</nav>'''


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
  font-size: 30px !important;
  font-weight: 700 !important;
  margin: 0 !important;
  color: #1a4d2e !important;
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
body.wsite-page-team .team-legend {
  color: #6b7571;
  font-size: 13px;
  margin-left: 4px;
}

/* Bottom names nav customisations (builds on .section-nav base styles) */
body.wsite-page-team .team-names-nav ol {
  justify-content: flex-start;
}
body.wsite-page-team .team-names-nav a {
  font-family: 'Raleway', -apple-system, sans-serif !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  font-size: 12px !important;
  font-weight: 500;
}

/* In Memoriam — dedicated full-page segment for Martin Fortier */
body.wsite-page-team .memoriam {
  max-width: 960px;
  margin: 96px auto 64px;
  padding: 0 24px;
  scroll-margin-top: 24px;
  scroll-margin-bottom: 120px;
}
body.wsite-page-team .memoriam__divider {
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(26, 77, 46, 0.25), transparent);
  margin: 0 auto 48px;
  max-width: 320px;
}
body.wsite-page-team .memoriam__eyebrow {
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 0.16em !important;
  text-transform: uppercase !important;
  color: #7b8c89 !important;
  margin: 0 0 8px !important;
  text-align: center !important;
}
body.wsite-page-team .memoriam__name {
  font-size: 38px !important;
  font-weight: 700 !important;
  color: #1a4d2e !important;
  margin: 0 0 4px !important;
  letter-spacing: -0.02em !important;
  text-transform: none !important;
  text-align: center !important;
  line-height: 1.1 !important;
}
body.wsite-page-team .memoriam__role {
  font-size: 14px !important;
  color: #6b7571 !important;
  margin: 0 0 48px !important;
  font-weight: 400 !important;
  text-align: center !important;
}

/* Hero block with photo + opening tribute */
body.wsite-page-team .memoriam__hero {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 40px;
  align-items: start;
  margin: 0 auto 56px;
  max-width: 820px;
}
body.wsite-page-team .memoriam__photo {
  width: 220px;
  height: 220px;
  border-radius: 50%;
  overflow: hidden;
  background: #f2f4f3;
  box-shadow: 0 0 0 4px #8fbf4d, 0 10px 30px rgba(26, 77, 46, 0.15);
}
body.wsite-page-team .memoriam__photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 25%;
  display: block;
  max-width: none !important;
  border-radius: 50%;
}
body.wsite-page-team .memoriam__lede p {
  font-size: 16px !important;
  line-height: 1.7 !important;
  color: #1f2826 !important;
  margin: 0 0 18px !important;
  text-align: left !important;
}
body.wsite-page-team .memoriam__primary {
  display: inline-block;
  padding: 10px 18px;
  border: 1px solid #3d8b3d;
  border-radius: 6px;
  color: #1a4d2e !important;
  text-decoration: none !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  letter-spacing: 0.02em;
  transition: background 120ms ease, color 120ms ease;
}
body.wsite-page-team .memoriam__primary:hover {
  background: #3d8b3d;
  color: #ffffff !important;
}

/* Body columns under the hero */
body.wsite-page-team .memoriam__col {
  max-width: 68ch;
  margin: 0 auto 40px;
}
body.wsite-page-team .memoriam__subhead {
  font-family: 'Raleway', sans-serif !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  color: #1a4d2e !important;
  margin: 0 0 12px !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
}
body.wsite-page-team .memoriam__col p {
  font-size: 15px !important;
  line-height: 1.72 !important;
  color: #2a3330 !important;
  margin: 0 0 14px !important;
  text-align: left !important;
  font-weight: 400 !important;
}
body.wsite-page-team .memoriam__works {
  list-style: disc !important;
  padding-left: 24px !important;
  margin: 0 !important;
}
body.wsite-page-team .memoriam__works li {
  font-size: 14.5px !important;
  line-height: 1.65 !important;
  color: #2a3330 !important;
  margin: 0 0 10px !important;
  padding: 0 !important;
  list-style: disc !important;
}
body.wsite-page-team .memoriam__works em {
  color: #1a4d2e;
  font-style: italic;
}

/* Personal tribute — blockquote */
body.wsite-page-team .memoriam__tribute {
  background: rgba(143, 191, 77, 0.06);
  border-left: 3px solid #8fbf4d;
  border-radius: 6px;
  padding: 28px 32px;
  max-width: 68ch;
}
body.wsite-page-team .memoriam__tribute .memoriam__subhead {
  margin-top: 0 !important;
}
body.wsite-page-team .memoriam__tribute blockquote {
  margin: 0;
  padding: 0;
  border: none;
}
body.wsite-page-team .memoriam__tribute blockquote p {
  font-style: italic;
  font-size: 15px !important;
  line-height: 1.7 !important;
  color: #2a3330 !important;
  margin: 0 0 14px !important;
}
body.wsite-page-team .memoriam__tribute footer {
  font-size: 13px;
  color: #6b7571;
  margin-top: 8px;
  font-style: normal;
}

@media (max-width: 700px) {
  body.wsite-page-team .memoriam { margin: 56px auto 48px; padding: 0 16px; }
  body.wsite-page-team .memoriam__name { font-size: 30px !important; }
  body.wsite-page-team .memoriam__hero {
    grid-template-columns: 1fr;
    justify-items: center;
    gap: 24px;
  }
  body.wsite-page-team .memoriam__photo { width: 180px; height: 180px; }
  body.wsite-page-team .memoriam__lede p { text-align: left !important; }
  body.wsite-page-team .memoriam__tribute { padding: 22px 20px; }
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

/* --- ALIUS palette (sampled from the leaf logo) ---
   #1a4d2e  — dark forest green (ALIUS wordmark, darker leaf)
   #3d8b3d  — medium leaf green
   #8fbf4d  — bright leaf green (highlight)
   #0f1a11  — near black
   #ffffff  — white (background)
*/

/* Card (viscereality pattern: left-accent colored border) */
body.wsite-page-team .team-card {
  background: #ffffff;
  border: 1px solid rgba(26, 77, 46, 0.12);
  border-left: 3px solid #3d8b3d;  /* leaf-green left accent */
  border-radius: 10px;
  padding: 24px 20px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
  text-shadow: 0 0 2px rgba(26, 77, 46, 0.02);
}
body.wsite-page-team .team-card--coord {
  border-left-color: #8fbf4d;  /* brighter leaf green for coordinators */
  border-left-width: 4px;
}
body.wsite-page-team .team-card:hover {
  border-color: rgba(26, 77, 46, 0.25);
  border-left-color: #3d8b3d;
  box-shadow: 0 6px 22px -6px rgba(26, 77, 46, 0.25), 0 0 0 1px rgba(61, 139, 61, 0.1);
  transform: translateY(-3px);
}
body.wsite-page-team .team-card--coord:hover {
  border-left-color: #8fbf4d;
  box-shadow: 0 6px 22px -6px rgba(143, 191, 77, 0.4), 0 0 0 1px rgba(143, 191, 77, 0.2);
}

body.wsite-page-team .team-card__avatar {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  background: #f2f4f3;
  margin-bottom: 14px;
  /* Ring matches card accent (leaf green) */
  box-shadow: 0 0 0 3px #3d8b3d, 0 2px 6px rgba(0, 0, 0, 0.08);
}
body.wsite-page-team .team-card--coord .team-card__avatar {
  box-shadow: 0 0 0 3px #8fbf4d, 0 2px 6px rgba(0, 0, 0, 0.08);
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
  font-size: 15px !important;
  font-weight: 700 !important;
  color: #0f1a11 !important;
  margin: 0 0 4px !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  line-height: 1.3 !important;
}
body.wsite-page-team .team-card__role {
  font-size: 11.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase !important;
  color: #3d8b3d !important;
  margin: 0 0 12px !important;
}
body.wsite-page-team .team-card--coord .team-card__role {
  color: #6b9b1f !important;
}
body.wsite-page-team .team-card__role--muted {
  color: #6b7571 !important;
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
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  color: #6b7571;
  background: #ffffff;
  cursor: pointer;
  transition: color 120ms ease, border-color 120ms ease,
              background 120ms ease, box-shadow 120ms ease;
}
body.wsite-page-team .team-card__icon:hover,
body.wsite-page-team .team-card__icon:focus-visible {
  color: #1f2826;
  outline: none;
}
body.wsite-page-team .team-card__icon svg {
  width: 16px;
  height: 16px;
}

/* Brand-coloured hover glow per platform (matches viscereality.org pattern) */
body.wsite-page-team .team-card__icon--linkedin:hover {
  border-color: rgba(0, 119, 181, 0.8);
  color: #0077b5;
  box-shadow: 0 0 0 3px rgba(0, 119, 181, 0.15);
}
body.wsite-page-team .team-card__icon--scholar:hover {
  border-color: rgba(66, 133, 244, 0.8);
  color: #4285f4;
  box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.15);
}
body.wsite-page-team .team-card__icon--orcid:hover {
  border-color: rgba(166, 206, 57, 0.8);
  color: #a6ce39;
  box-shadow: 0 0 0 3px rgba(166, 206, 57, 0.15);
}
body.wsite-page-team .team-card__icon--researchgate:hover {
  border-color: rgba(0, 204, 187, 0.8);
  color: #00ccbb;
  box-shadow: 0 0 0 3px rgba(0, 204, 187, 0.15);
}
body.wsite-page-team .team-card__icon--twitter:hover {
  border-color: rgba(0, 0, 0, 0.6);
  color: #000000;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
body.wsite-page-team .team-card__icon--github:hover {
  border-color: rgba(36, 41, 46, 0.8);
  color: #24292e;
  box-shadow: 0 0 0 3px rgba(36, 41, 46, 0.12);
}
body.wsite-page-team .team-card__icon--academia:hover {
  border-color: rgba(65, 69, 74, 0.7);
  color: #41454a;
}
body.wsite-page-team .team-card__icon--site:hover,
body.wsite-page-team .team-card__icon--pdf:hover {
  border-color: rgba(92, 120, 114, 0.7);
  color: #5c7872;
}
body.wsite-page-team .team-card__icon--email:hover {
  border-color: rgba(92, 120, 114, 0.7);
  color: #5c7872;
}

/* Email hover-reveal tooltip (anti-scraper: no mailto, no raw address in href) */
body.wsite-page-team .team-card__icon--email {
  cursor: help;
}
body.wsite-page-team .team-card__email-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 10px;
  background: #1f2826;
  color: #ffffff;
  font-size: 12px;
  white-space: nowrap;
  border-radius: 4px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 120ms ease;
  z-index: 5;
}
body.wsite-page-team .team-card__email-tooltip::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: #1f2826;
}
body.wsite-page-team .team-card__icon--email:hover .team-card__email-tooltip,
body.wsite-page-team .team-card__icon--email:focus-visible .team-card__email-tooltip {
  opacity: 1;
}

/* Coordinator asterisk on card name */
body.wsite-page-team .team-card__coord {
  color: #7b8c89;
  font-weight: 500;
  font-size: 13px;
  margin-left: 2px;
}

/* Alphabetical names-index (multi-column) — click to jump to that member's card */
body.wsite-page-team .team-index {
  max-width: 1200px;
  margin: 24px auto 0;
  padding: 0 24px;
}
body.wsite-page-team .team-index__legend {
  font-size: 12px !important;
  color: #6b7571 !important;
  margin: 0 0 12px !important;
  text-align: center !important;
  font-weight: 400 !important;
}
body.wsite-page-team .team-index__list {
  columns: 3;
  column-gap: 32px;
  margin: 0 !important;
  padding: 0 !important;
  list-style: none !important;
}
body.wsite-page-team .team-index__list li {
  break-inside: avoid;
  padding: 4px 0;
  text-align: center;
  list-style: none !important;
  margin: 0 !important;
}
body.wsite-page-team .team-index__list a {
  color: #2a3330;
  text-decoration: none;
  font-size: 13.5px;
  line-height: 1.7;
  transition: color 120ms ease;
  border-bottom: 1px solid transparent;
}
body.wsite-page-team .team-index__list a:hover,
body.wsite-page-team .team-index__list a:focus-visible {
  color: #111a18;
  border-bottom-color: rgba(0, 0, 0, 0.3);
  outline: none;
}
@media (max-width: 720px) {
  body.wsite-page-team .team-index__list { columns: 2; column-gap: 20px; }
}
@media (max-width: 420px) {
  body.wsite-page-team .team-index__list { columns: 1; }
}

/* Scroll anchor offset so jumps don't land under sticky bottom nav */
body.wsite-page-team .team-card {
  scroll-margin-top: 16px;
  scroll-margin-bottom: 96px;
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
    """Produce the team page body: one alphabetical grid of all members
    (coordinators flagged inline), plus a separate In Memoriam section for
    Martin Fortier. No top names index — the bottom nav carries names."""
    import html as _html

    parts: list[str] = []
    parts.append(CSS)
    parts.append('<div class="team-page-title"><h1>The ALIUS Team</h1><p>All members listed alphabetically. <span class="team-legend">Coordinators marked with *</span></p></div>')

    # Gather every unique member from Coordinators + Research Members into one
    # list; flag coordinators so we can mark them inline on their cards.
    seen_names: set[str] = set()
    all_members: list[dict] = []
    coord_keys: set[str] = set()
    in_memoriam: list[dict] = []
    for label, anchor, source_dir in SOURCES:
        mode = "single" if anchor == "in-memoriam" else "members"
        members = parse_source(source_dir, mode=mode)
        if not members:
            continue
        for m in members:
            key = re.sub(r"[^a-z0-9]+", "", (m.get("name") or "").lower())
            if not key:
                continue
            if anchor == "in-memoriam":
                in_memoriam.append(m)
                continue
            if label == "Coordinators":
                coord_keys.add(key)
            if key in seen_names:
                continue
            seen_names.add(key)
            all_members.append(m)

    # Fold in the extras (Paweł Motyka, France Lerner, ...) if not already present
    for em in EXTRA_MEMBERS:
        key = re.sub(r"[^a-z0-9]+", "", em["name"].lower())
        if key in seen_names:
            continue
        seen_names.add(key)
        all_members.append(em)

    # Sort by family name (last word) case-insensitively
    def sort_key(m):
        name = _html.unescape(re.sub(r"<[^>]+>", "", m.get("name") or ""))
        parts_ = name.strip().split()
        return (parts_[-1].lower() if parts_ else "", name.lower())
    all_members.sort(key=sort_key)

    # Single grid of all members
    parts.append('<div class="team-grid">')
    for m in all_members:
        key = re.sub(r"[^a-z0-9]+", "", (m.get("name") or "").lower())
        parts.append(render_card(m, is_coordinator=(key in coord_keys)))
    parts.append('</div>')

    # In Memoriam section (Martin Fortier) — dedicated bottom segment
    if in_memoriam:
        parts.append(render_memoriam(in_memoriam[0]))

    # Bottom pane: alphabetical names nav (one link per member; jumps to card)
    # Build here so it gets embedded inline; the CSS positions it fixed-bottom.
    parts.append(render_bottom_names_nav(all_members, coord_keys))

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
