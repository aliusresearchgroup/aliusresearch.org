"""Consolidate 4 team-related pages into a single /team/ page.

Sources:
- site-src/content/about/team/team-222796/body.html  (Coordinators)
- site-src/content/about/team/team-955042/body.html  (Research Members + Honorary)
- site-src/content/pages/martinfortier/body.html     (In Memoriam: Martin Fortier)

Output:
- site-src/content/team/body.html
- site-src/content/team/head.raw.html
- site-src/content/team/index.page.json

Approach:
- Extract <div id="wsite-content"...> content blocks from each source
- Extract all <div class="wsite-section-wrap"> blocks (these hold the member
  entries, styled exactly as on the existing live site)
- Use team-222796's head.raw.html as the shell (correct CSS/JS for all content)
- Replace the content block with concatenation of all extracted sections, in
  a curated order with section dividers
- The wrapping HTML (header, nav, footer, body scripts) is inherited verbatim
  from team-222796, so appearance of the page shell is identical.
"""
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "site-src" / "content"
OUT = REPO / "site-src" / "content" / "team"
OUT.mkdir(parents=True, exist_ok=True)

SHELL_DIR = SRC / "about" / "team" / "team-222796"

SOURCES_REWRITTEN = [
    ("Coordinators", SRC / "about" / "team" / "team-222796" / "original.rewritten.html"),
    ("Research Members", SRC / "about" / "team" / "team-955042" / "original.rewritten.html"),
    ("In Memoriam: Martin Fortier", SRC / "pages" / "martinfortier" / "original.rewritten.html"),
]

SOURCES_BODY = [
    ("Coordinators", SRC / "about" / "team" / "team-222796" / "body.html"),
    ("Research Members", SRC / "about" / "team" / "team-955042" / "body.html"),
    ("In Memoriam: Martin Fortier", SRC / "pages" / "martinfortier" / "body.html"),
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_content_sections(body: str) -> str:
    """Return the raw HTML between <div id="wsite-content"...> and its close."""
    m = re.search(
        r'<div\s+id="wsite-content"[^>]*>(.*?)(?=</div>\s*</div>\s*<div\s+id="footer")',
        body,
        flags=re.DOTALL,
    )
    if not m:
        raise RuntimeError("Could not locate wsite-content block")
    return m.group(1)


def extract_section_wraps(content: str) -> list[str]:
    """Return a list of <div class="wsite-section-wrap">...</div> blocks."""
    sections: list[str] = []
    idx = 0
    while True:
        start = content.find('<div class="wsite-section-wrap">', idx)
        if start == -1:
            break
        # Find matching </div> by balancing div nesting
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


def make_section_divider(title: str) -> str:
    """Return a <div class="wsite-section-wrap"> with a large centered title."""
    return f'''<div class="wsite-section-wrap">
	<div class="wsite-section wsite-body-section wsite-custom-background">
		<div class="wsite-section-content">
			<div class="container">
				<div class="wsite-section-elements">
					<h2 class="wsite-content-title" style="text-align:center;"><strong style="color:rgb(123, 140, 137)"><font size="6">{title}</font></strong></h2>
					<div><div style="height: 10px; overflow: hidden; width: 100%;"></div>
					<hr class="styled-hr" style="width:100%;"></hr>
					<div style="height: 10px; overflow: hidden; width: 100%;"></div></div>
				</div>
			</div>
		</div>
	</div>
</div>
'''


def _assemble(shell_text: str, sources: list) -> str:
    shell_content_start = shell_text.find('<div id="wsite-content"')
    pre = shell_text[:shell_content_start]
    rest = shell_text[shell_content_start:]
    m = re.search(
        r'(<div\s+id="wsite-content"[^>]*>).*?(</div>\s*</div>\s*<div\s+id="footer")',
        rest,
        flags=re.DOTALL,
    )
    if not m:
        raise RuntimeError("Could not parse shell")
    open_tag = m.group(1)
    after_content_start = shell_content_start + m.start(2)
    post = shell_text[after_content_start:]

    # Consolidated page title + header as first section
    consolidated_sections: list[str] = []
    consolidated_sections.append(f'''<div class="wsite-section-wrap">
	<div class="wsite-section wsite-body-section wsite-custom-background">
		<div class="wsite-section-content">
			<div class="container">
				<div class="wsite-section-elements">
					<h2 class="wsite-content-title" style="text-align:center;"><strong style="color:rgb(81, 81, 81)"><font size="7">The ALIUS Team</font></strong></h2>
					<div><div style="height: 20px; overflow: hidden; width: 100%;"></div>
					<hr class="styled-hr" style="width:100%;"></hr>
					<div style="height: 20px; overflow: hidden; width: 100%;"></div></div>
				</div>
			</div>
		</div>
	</div>
</div>
''')

    for section_title, source_path in sources:
        source_body = read(source_path)
        content = extract_content_sections(source_body)
        sections = extract_section_wraps(content)
        consolidated_sections.append(make_section_divider(section_title))
        consolidated_sections.extend(sections)

    new_text = pre + open_tag + "\n" + "\n".join(consolidated_sections) + "\n" + post
    new_text = re.sub(r"<title>[^<]*</title>", "<title>Team - Alius</title>", new_text, count=1)
    return new_text


def build_body() -> str:
    return _assemble(read(SHELL_DIR / "body.html"), SOURCES_BODY)


def build_rewritten() -> str:
    return _assemble(read(SHELL_DIR / "original.rewritten.html"), SOURCES_REWRITTEN)


def build_original() -> str:
    return _assemble(read(SHELL_DIR / "original.html"), SOURCES_BODY)


def build_head() -> str:
    head = read(SHELL_DIR / "head.raw.html")
    head = re.sub(r"<title>[^<]*</title>", "<title>Team - Alius</title>", head, count=1)
    return head


def build_page_json() -> dict:
    shell_json = json.loads(read(SHELL_DIR / "index.page.json"))
    shell_json["id"] = "team"
    shell_json["legacy_path"] = "team.html"
    shell_json["legacy_name"] = "team"
    shell_json["canonical_path"] = "/team/"
    shell_json["title"] = "Team - Alius"
    shell_json["body_fragment"] = "content/team/body.html"
    shell_json["head_fragment"] = "content/team/head.raw.html"
    shell_json["source_html"] = "content/team/original.html"
    shell_json["body_tag_attributes"] = 'class="no-header  wsite-page-team  full-width-on  wsite-theme-light"'
    shell_json["redirect_legacy"] = True
    return shell_json


def main():
    write(OUT / "body.html", build_body())
    write(OUT / "head.raw.html", build_head())
    write(OUT / "index.page.json", json.dumps(build_page_json(), indent=4))
    write(OUT / "original.html", build_original())
    write(OUT / "original.rewritten.html", build_rewritten())
    print(f"Built consolidated team page at {OUT}/")
    print(f"  body.html: {(OUT / 'body.html').stat().st_size:,} bytes")
    print(f"  original.rewritten.html: {(OUT / 'original.rewritten.html').stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
