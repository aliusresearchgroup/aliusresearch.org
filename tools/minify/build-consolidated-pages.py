"""Generic consolidator: merges multiple source pages into a single main-tab
page, following the same pattern used for the team page.

Runs for all 3 remaining tabs: Bulletin, Events, Membership.

For each tab config:
- Uses the 'shell' page as the HTML skeleton (provides nav, head, footer, scripts)
- Extracts <div class="wsite-section-wrap"> content blocks from each source's
  original.rewritten.html (which has rewritten absolute paths)
- Inserts section-divider headers between each source's content
- Writes body.html, original.html, original.rewritten.html, head.raw.html, index.page.json
- Adds sticky section nav + smooth scroll CSS (reused team styling pattern)

The caller (build-site.ps1) reads rewritten-page-sources.csv to decide which
original.rewritten.html to serve for each legacy URL.
"""
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "site-src" / "content"

# ------------------- Configs -------------------

CONFIGS = [
    {
        "id": "bulletin",
        "canonical_path": "/bulletin/",
        "legacy_path": "bulletin.html",
        "title": "Bulletin - Alius",
        "page_heading": "The ALIUS Bulletin",
        "anchor_nav": [
            ("Issue n°7", "bulletin-07"),
            ("Issue n°6", "bulletin-06"),
            ("Issue n°5", "bulletin-05"),
            ("Issue n°4", "bulletin-04"),
            ("Issue n°3", "bulletin-03"),
            ("Issue n°2", "bulletin-02"),
            ("Issue n°1", "bulletin-01"),
        ],
        "shell_dir": SRC / "bulletin",
        "sources": [
            # (section_title, anchor_id, source_dir)
            ("Bulletin Issue n°7", "bulletin-07", SRC / "bulletin" / "issues" / "bulletin-07"),
            ("Bulletin Issue n°6", "bulletin-06", SRC / "bulletin" / "issues" / "bulletin-06"),
            ("Bulletin Issue n°5", "bulletin-05", SRC / "bulletin" / "issues" / "bulletin-05"),
            ("Bulletin Issue n°4", "bulletin-04", SRC / "bulletin" / "issues" / "bulletin-04"),
            ("Bulletin Issue n°3", "bulletin-03", SRC / "bulletin" / "issues" / "bulletin-03"),
            ("Bulletin Issue n°2", "bulletin-02", SRC / "bulletin" / "issues" / "bulletin-02"),
            ("Bulletin Issue n°1", "bulletin-01", SRC / "bulletin" / "issues" / "bulletin-01"),
        ],
        "out_dir": SRC / "_consolidated" / "bulletin",
        "body_class": "wsite-page-bulletin",
    },
    {
        "id": "events",
        "canonical_path": "/events/",
        "legacy_path": "events.html",
        "title": "Events - Alius",
        "page_heading": "Events",
        "anchor_nav": [
            ("ASSC Satellite", "assc-satellite"),
            ("Program", "program"),
            ("Attendees", "attendees"),
            ("Travel", "travel"),
            ("Music", "music"),
        ],
        "shell_dir": SRC / "events" / "events",
        "sources": [
            ("ASSC Satellite", "assc-satellite", SRC / "research" / "projects" / "qualius"),
            ("Program Information", "program", SRC / "research" / "projects" / "qualius-program"),
            ("Attendees", "attendees", SRC / "events" / "attendees"),
            ("Travel Information", "travel", SRC / "events" / "travel-information"),
            ("Music", "music", SRC / "media" / "music"),
        ],
        "out_dir": SRC / "_consolidated" / "events",
        "body_class": "wsite-page-events",
    },
    {
        "id": "membership",
        "canonical_path": "/membership/",
        "legacy_path": "membership-renewal-894351.html",
        "title": "Membership - Alius",
        "page_heading": "Membership",
        "anchor_nav": [
            ("Active Roles", "active-roles"),
            ("Researcher Membership", "researcher-membership"),
        ],
        "shell_dir": SRC / "community" / "membership-renewal-894351",
        "sources": [
            ("Active Roles", "active-roles", SRC / "pages" / "active-roles"),
            ("Researcher Membership", "researcher-membership", SRC / "community" / "membership-renewal-178580"),
        ],
        "out_dir": SRC / "_consolidated" / "membership",
        "body_class": "wsite-page-membership",
    },
]

# ------------------- Helpers -------------------

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_content_sections(body: str) -> str:
    m = re.search(
        r'<div\s+id="wsite-content"[^>]*>(.*?)(?=</div>\s*</div>\s*<div\s+id="footer")',
        body,
        flags=re.DOTALL,
    )
    if not m:
        raise RuntimeError("Could not locate wsite-content block")
    return m.group(1)


def extract_section_wraps(content: str) -> list[str]:
    sections: list[str] = []
    idx = 0
    while True:
        start = content.find('<div class="wsite-section-wrap">', idx)
        if start == -1:
            break
        depth = 0
        i = start
        while i < len(content):
            nxt_open = content.find("<div", i + 1)
            nxt_close = content.find("</div>", i + 1)
            if nxt_close == -1:
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                i = nxt_open
            else:
                if depth == 0:
                    end = nxt_close + len("</div>")
                    sections.append(content[start:end])
                    idx = end
                    break
                depth -= 1
                i = nxt_close
        else:
            break
    return sections


def make_divider(title: str, anchor: str) -> str:
    return f'''<span id="{anchor}" class="tab-anchor"></span>
<div class="wsite-section-wrap">
	<div class="wsite-section wsite-body-section wsite-custom-background">
		<div class="wsite-section-content">
			<div class="container">
				<div class="wsite-section-elements">
					<h2 class="wsite-content-title" style="text-align:center;"><strong style="color:rgb(123, 140, 137)"><font size="6">{title}</font></strong></h2>
					<hr class="styled-hr" style="width:100%;"></hr>
				</div>
			</div>
		</div>
	</div>
</div>
'''


def make_heading(title: str) -> str:
    return f'''<div class="wsite-section-wrap">
	<div class="wsite-section wsite-body-section wsite-custom-background">
		<div class="wsite-section-content">
			<div class="container">
				<div class="wsite-section-elements">
					<h2 class="wsite-content-title" style="text-align:center;"><strong style="color:rgb(81, 81, 81)"><font size="7">{title}</font></strong></h2>
					<hr class="styled-hr" style="width:100%;"></hr>
				</div>
			</div>
		</div>
	</div>
</div>
'''


def build_nav(anchor_nav: list[tuple[str, str]]) -> str:
    items = "\n  ".join(
        f'<li><a href="#{anchor}">{title}</a></li>'
        for title, anchor in anchor_nav
    )
    return f'<ul class="tab-section-nav">\n  {items}\n</ul>\n'


STYLE_BLOCK = """<style>
/* Main-tab consolidated pages: sticky section nav + smooth scroll */
html { scroll-behavior: smooth; }
.tab-section-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1.2rem;
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
.tab-section-nav a {
  color: #42514c;
  text-decoration: none;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  transition: background 160ms ease, color 160ms ease;
}
.tab-section-nav a:hover,
.tab-section-nav a:focus {
  background: rgba(123, 140, 137, 0.15);
  color: #2a3330;
}
.tab-anchor {
  position: relative;
  top: -72px;
  visibility: hidden;
  pointer-events: none;
  display: block;
  height: 0;
}
.wsite-section-wrap { scroll-margin-top: 80px; }
@media (max-width: 640px) {
  .tab-section-nav {
    gap: 0.5rem;
    font-size: 11px;
    padding: 0.6rem 0.5rem;
  }
}
</style>
"""

def assemble(shell_text: str, cfg: dict) -> str:
    m = re.search(
        r'(<div\s+id="wsite-content"[^>]*>).*?(</div>\s*</div>\s*<div\s+id="footer")',
        shell_text,
        flags=re.DOTALL,
    )
    if not m:
        raise RuntimeError("Could not parse shell wsite-content block")
    pre = shell_text[:m.start()]
    open_tag = m.group(1)
    post = shell_text[m.start(2):]

    pieces: list[str] = []
    pieces.append(build_nav(cfg["anchor_nav"]))
    pieces.append(make_heading(cfg["page_heading"]))
    for section_title, anchor, source_dir in cfg["sources"]:
        # Prefer rewritten html when available (has absolute-path links)
        for fname in ("original.rewritten.html", "body.html"):
            src = source_dir / fname
            if src.exists():
                break
        else:
            print(f"  ! no source for {source_dir}")
            continue
        pieces.append(make_divider(section_title, anchor))
        try:
            content = extract_content_sections(read(src))
        except Exception as e:
            print(f"  ! failed to extract from {src}: {e}")
            continue
        sections = extract_section_wraps(content)
        if not sections:
            # Fallback: include the whole content block
            pieces.append(content)
        else:
            pieces.extend(sections)

    new = pre + open_tag + "\n" + "\n".join(pieces) + "\n" + post
    new = re.sub(r"<title>[^<]*</title>", f'<title>{cfg["title"]}</title>', new, count=1)
    # Update body class
    new = re.sub(
        r'<body class="([^"]*)">',
        lambda mm: f'<body class="{cfg["body_class"]} {mm.group(1).split()[0] if mm.group(1) else ""} full-width-on wsite-theme-light">',
        new,
        count=1,
    )
    # Inject style block before </head>
    if "tab-section-nav" not in new:
        new = new.replace("</head>", STYLE_BLOCK + "</head>", 1)
    return new


def build_page_json(cfg: dict) -> dict:
    shell_json = json.loads(read(cfg["shell_dir"] / "index.page.json"))
    shell_json["id"] = cfg["id"]
    shell_json["legacy_path"] = cfg["legacy_path"]
    shell_json["legacy_name"] = cfg["id"]
    shell_json["canonical_path"] = cfg["canonical_path"]
    shell_json["title"] = cfg["title"]
    shell_json["body_fragment"] = f'content/_consolidated/{cfg["id"]}/body.html'
    shell_json["head_fragment"] = f'content/_consolidated/{cfg["id"]}/head.raw.html'
    shell_json["source_html"] = f'content/_consolidated/{cfg["id"]}/original.html'
    shell_json["body_tag_attributes"] = f'class="{cfg["body_class"]}  full-width-on  wsite-theme-light"'
    shell_json["redirect_legacy"] = True
    return shell_json


def process(cfg: dict) -> None:
    shell = cfg["shell_dir"]
    out = cfg["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    body_shell = read(shell / "body.html")
    rewritten_shell = read(shell / "original.rewritten.html")
    original_shell = read(shell / "original.html") if (shell / "original.html").exists() else rewritten_shell

    write(out / "body.html", assemble(body_shell, cfg))
    write(out / "original.rewritten.html", assemble(rewritten_shell, cfg))
    write(out / "original.html", assemble(original_shell, cfg))
    # head.raw.html copied from shell with title swap
    head = read(shell / "head.raw.html")
    head = re.sub(r"<title>[^<]*</title>", f'<title>{cfg["title"]}</title>', head, count=1)
    write(out / "head.raw.html", head)
    write(out / "index.page.json", json.dumps(build_page_json(cfg), indent=4))
    print(f"  built /{cfg['id']}/  -> {out}")


def main():
    for cfg in CONFIGS:
        print(f"==> {cfg['id']}")
        process(cfg)


if __name__ == "__main__":
    main()
