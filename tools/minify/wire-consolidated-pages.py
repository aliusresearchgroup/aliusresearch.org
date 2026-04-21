"""Update pages.json, rewritten-page-sources.csv, and redirects.json to route
the main-tab legacy URLs to the new consolidated pages at /bulletin/, /events/,
/membership/.
"""
import csv
import io
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "site-src" / "data"
MIGRATION = REPO / "migration"

# (legacy_path, new_canonical, new_source_rel_to_site-src)
MAIN_ROUTES = [
    ("bulletin.html", "/bulletin/", "content/_consolidated/bulletin"),
    ("events.html",   "/events/",   "content/_consolidated/events"),
    ("membership-renewal-894351.html", "/membership/", "content/_consolidated/membership"),
    ("journal-club.html", "/journal-club/", "content/events/journal-club"),
]

# Legacy URLs to redirect INTO the new consolidated pages
REDIRECT_INTO = {
    "/bulletin/": [
        "/bulletin.html", "/bulletin01.html", "/bulletin02.html", "/bulletin03.html",
        "/bulletin04.html", "/bulletin05.html", "/bulletin06.html", "/bulletin07.html",
        "/froese.html", "/changeux.html",
        "/bulletin/issues/bulletin-01/", "/bulletin/issues/bulletin-02/",
        "/bulletin/issues/bulletin-03/", "/bulletin/issues/bulletin-04/",
        "/bulletin/issues/bulletin-05/", "/bulletin/issues/bulletin-06/",
        "/bulletin/issues/bulletin-07/",
        "/pages/froese/", "/pages/changeux/",
    ],
    "/events/": [
        "/events.html", "/qualius.html", "/qualius-program.html",
        "/attendees.html", "/travel-information.html", "/music.html",
        "/events/events/", "/events/attendees/", "/events/travel-information/",
        "/research/projects/qualius/", "/research/projects/qualius-program/",
        "/media/music/",
    ],
    "/membership/": [
        "/membership-renewal-894351.html", "/membership-renewal-178580.html",
        "/active-roles.html",
        "/community/membership-renewal-894351/",
        "/community/membership-renewal-178580/",
        "/pages/active-roles/",
    ],
    "/journal-club/": [
        "/journal-club.html", "/events/journal-club/",
    ],
}


def update_pages_json():
    path = DATA / "pages.json"
    pages = json.loads(path.read_text(encoding="utf-8-sig"))
    route_to_cfg = {
        "bulletin.html": ("bulletin", "/bulletin/", "content/_consolidated/bulletin"),
        "events.html":   ("events",   "/events/",   "content/_consolidated/events"),
        "membership-renewal-894351.html": ("membership", "/membership/", "content/_consolidated/membership"),
        "journal-club.html": ("journal-club", "/journal-club/", "content/events/journal-club"),
    }
    updated = 0
    for p in pages:
        legacy = p.get("legacy_path")
        if legacy in route_to_cfg:
            new_id, canon, src = route_to_cfg[legacy]
            p["canonical_path"] = canon
            p["body_fragment"] = f"{src}/body.html"
            p["head_fragment"] = f"{src}/head.raw.html"
            p["source_html"] = f"{src}/original.html"
            updated += 1
    path.write_text(json.dumps(pages, indent=4), encoding="utf-8")
    print(f"pages.json: updated {updated} entries")


def update_rewritten_csv():
    path = MIGRATION / "rewritten-page-sources.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    # First line is header
    header = lines[0]
    rows = []
    updated = 0
    new_sources = {
        "bulletin.html":                  ("/bulletin/",   "content/_consolidated/bulletin/original.html",   "content/_consolidated/bulletin/original.rewritten.html"),
        "events.html":                    ("/events/",     "content/_consolidated/events/original.html",     "content/_consolidated/events/original.rewritten.html"),
        "membership-renewal-894351.html": ("/membership/", "content/_consolidated/membership/original.html", "content/_consolidated/membership/original.rewritten.html"),
        "journal-club.html":              ("/journal-club/","content/events/journal-club/original.html","content/events/journal-club/original.rewritten.html"),
    }
    for line in lines[1:]:
        row = next(csv.reader(io.StringIO(line)))
        if len(row) < 4:
            rows.append(line)
            continue
        legacy = row[0]
        if legacy in new_sources:
            canon, orig, rew = new_sources[legacy]
            row = [legacy, canon, orig, rew]
            updated += 1
        rows.append(",".join(f'"{c}"' for c in row))
    out = "\n".join([header] + rows) + "\n"
    path.write_text(out, encoding="utf-8")
    print(f"rewritten-page-sources.csv: updated {updated} rows")


def update_redirects():
    path = DATA / "redirects.json"
    redirects = json.loads(path.read_text(encoding="utf-8-sig"))
    # Build a map of existing redirects by 'from'
    existing = {r["from"]: r for r in redirects}
    updated = added = 0
    for target, sources in REDIRECT_INTO.items():
        for src in sources:
            if src == target:
                continue
            if src in existing:
                if existing[src]["to"] != target:
                    existing[src]["to"] = target
                    updated += 1
            else:
                redirects.append({"from": src, "to": target, "type": "legacy-html-page"})
                added += 1
    path.write_text(json.dumps(redirects, indent=4), encoding="utf-8")
    print(f"redirects.json: updated {updated}, added {added}")


def main():
    update_pages_json()
    update_rewritten_csv()
    update_redirects()


if __name__ == "__main__":
    main()
