"""Retire the orphan/duplicate pages identified by the audit (A7).

For each orphan page:
  1. Remove its entry from site-src/data/pages.json so the build stops
     generating the HTML (the built docs/ file for that legacy path will
     be replaced by the redirect stub on next build).
  2. Remove its row from migration/rewritten-page-sources.csv.
  3. Add (or update) a redirects.json entry pointing the legacy URL to the
     canonical consolidated URL. The generate-redirects.ps1 pass then
     writes a stub at that path.

Safe: source content directories under site-src/content/ are left in place
for revertability. The only destructive change is to pages.json +
rewritten-page-sources.csv + redirects.json.
"""
import csv
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "site-src" / "data"
MIG = REPO / "migration"

# legacy_path  ->  canonical target URL
ORPHANS: dict[str, str] = {
    # Test/template pages
    "teamtest.html":            "/team/",
    "teamtest1.html":           "/team/",
    "teamtest2.html":           "/team/",
    "teamtemplate-956529.html": "/team/",
    # Duplicate team-member pages (no longer linked — replaced by /team/#member-<slug>)
    "team-639772.html":         "/team/",
    "team-743740.html":         "/team/",
    "team-814948.html":         "/team/",
    "team-912849.html":         "/team/",
    "team-955042-710461.html":  "/team/",
    # Bulletin interview duplicates (long numeric suffixes)
    "bulletin02-ratcliffeinterview-496999-868603-823482-372692.html":
        "/bulletin/interviews/bulletin02-ratcliffeinterview/",
    "bulletin06-gonzalez-interview-193094.html":
        "/bulletin/interviews/bulletin06-gonzalez-interview/",
    "bulletin06-dossinterview-532533.html":
        "/bulletin/",
    "bulletin06-koroma-podcast-348367.html":
        "/bulletin/interviews/bulletin06-koroma-podcast/",
    # Journal club duplicates — all point at /journal-club/
    "journal-club-228113.html":  "/journal-club/",
    "journal-club-995321.html":  "/journal-club/",
    "journalclub-868968.html":   "/journal-club/",
    # Membership duplicates — /membership/ is the consolidated page
    "membership-renewal-178580.html": "/membership/",
    # 894351 is already the source for /membership/; keep it
}


def update_pages_json() -> int:
    path = DATA / "pages.json"
    pages = json.loads(path.read_text(encoding="utf-8-sig"))
    before = len(pages)
    pages = [p for p in pages if p.get("legacy_path") not in ORPHANS]
    after = len(pages)
    path.write_text(json.dumps(pages, indent=4), encoding="utf-8")
    return before - after


def update_rewritten_csv() -> int:
    path = MIG / "rewritten-page-sources.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = lines[0]
    kept = []
    removed = 0
    for line in lines[1:]:
        row = next(csv.reader(io.StringIO(line)))
        if row and row[0] in ORPHANS:
            removed += 1
            continue
        kept.append(line)
    path.write_text("\n".join([header] + kept) + "\n", encoding="utf-8")
    return removed


def update_redirects() -> tuple[int, int]:
    path = DATA / "redirects.json"
    redirects = json.loads(path.read_text(encoding="utf-8-sig"))
    existing = {r["from"]: r for r in redirects}
    updated = added = 0
    for legacy, target in ORPHANS.items():
        from_url = "/" + legacy
        if from_url in existing:
            if existing[from_url]["to"] != target:
                existing[from_url]["to"] = target
                updated += 1
        else:
            redirects.append({"from": from_url, "to": target, "type": "orphan-retired"})
            added += 1
    path.write_text(json.dumps(redirects, indent=4), encoding="utf-8")
    return updated, added


def main():
    removed_pages = update_pages_json()
    removed_csv = update_rewritten_csv()
    upd, added = update_redirects()
    print(f"pages.json: removed {removed_pages} orphan entries")
    print(f"rewritten-page-sources.csv: removed {removed_csv} rows")
    print(f"redirects.json: updated {upd}, added {added}")


if __name__ == "__main__":
    main()
