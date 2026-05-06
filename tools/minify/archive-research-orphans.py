"""Archive all 26 /research/* pages — none are linked from the top nav.

The /events/ consolidated page already embeds the content of qualius.html
and qualius-program.html, so their standalone URLs are redundant.

Actions:
  - Remove all /research/ entries from site-src/data/pages.json
  - Remove from migration/rewritten-page-sources.csv
  - Add redirects.json entries pointing each old URL to a sensible target
  - Leave source content under site-src/content/research/projects/qualius*
    in place because build-consolidated-pages.py reads from them for /events/
  - Delete the generated docs/research/ tree on the next rebuild
"""
import csv
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "site-src" / "data"
MIG = REPO / "migration"

# legacy_path -> redirect target
RETIRE: dict[str, str] = {
    # Research landing + index
    "research.html":    "/",
    "research1.html":   "/",
    "projects.html":    "/",
    # Qualius content is now embedded in /events/
    "qualius.html":         "/events/#assc-satellite",
    "qualius-program.html": "/events/#program",
    # Individual research projects — all unreachable from top nav
    "anima.html":                                  "/",
    "cardiac_sleep.html":                          "/",
    "commentaries.html":                           "/",
    "commentaries2.html":                          "/",
    "cultural-shaping-of-consciousness.html":      "/events/#event-cultural-shaping-2019",
    "depersonalisation.html":                      "/",
    "mapping-dmt.html":                            "/",
    "meditation-psychedelics-self.html":           "/",
    "nichols-nichols-endogenous-dmt.html":         "/",
    "peripersonal.html":                           "/",
    "physiopheno.html":                            "/",
    "psychedelic-pharmacology.html":               "/",
    "psychedelics-challenging-experiences.html":   "/",
    "psychedelics-extrended-difficulties.html":    "/",
    "psychedelic-therapy.html":                    "/",
    "self-other.html":                             "/",
    "somatic-cultures-ad-consciousness.html":      "/events/#event-somatic-2021",
    "tagliazucchi_effects_psychedelics.html":      "/",
    "torus.html":                                  "/",
    "trauma_under_psychedelics.html":              "/",
    "viscereality.html":                           "/",
}


def update_pages_json() -> int:
    path = DATA / "pages.json"
    pages = json.loads(path.read_text(encoding="utf-8-sig"))
    before = len(pages)
    pages = [p for p in pages if p.get("legacy_path") not in RETIRE]
    path.write_text(json.dumps(pages, indent=4), encoding="utf-8")
    return before - len(pages)


def update_rewritten_csv() -> int:
    path = MIG / "rewritten-page-sources.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = lines[0]
    kept = []
    removed = 0
    for line in lines[1:]:
        row = next(csv.reader(io.StringIO(line)))
        if row and row[0] in RETIRE:
            removed += 1
            continue
        kept.append(line)
    path.write_text("\n".join([header] + kept) + "\n", encoding="utf-8")
    return removed


def update_redirects() -> tuple[int, int]:
    path = DATA / "redirects.json"
    redirects = json.loads(path.read_text(encoding="utf-8-sig"))
    existing = {r["from"]: r for r in redirects}
    upd = added = 0
    for legacy, target in RETIRE.items():
        src = "/" + legacy
        if src in existing:
            if existing[src]["to"] != target:
                existing[src]["to"] = target
                upd += 1
        else:
            redirects.append({"from": src, "to": target, "type": "archived-research"})
            added += 1
    # Also add canonical-form redirects so e.g. /research/projects/viscereality/ 301s
    for legacy, target in RETIRE.items():
        if legacy == "qualius.html":
            canon = "/research/projects/qualius/"
        elif legacy == "qualius-program.html":
            canon = "/research/projects/qualius-program/"
        elif legacy in ("research.html",):
            canon = "/research/"
        elif legacy in ("research1.html",):
            canon = "/research/research1/"
        elif legacy in ("projects.html", "commentaries.html", "commentaries2.html"):
            canon = f'/research/{"projects" if legacy=="projects.html" else "commentaries"}/{legacy.replace(".html","")}/' if legacy != "projects.html" else "/research/projects/"
        else:
            canon = f'/research/projects/{legacy.replace(".html","")}/'
        if canon == "/":
            continue
        if canon in existing:
            if existing[canon]["to"] != target:
                existing[canon]["to"] = target
                upd += 1
        else:
            redirects.append({"from": canon, "to": target, "type": "archived-research-canonical"})
            added += 1
    path.write_text(json.dumps(redirects, indent=4), encoding="utf-8")
    return upd, added


def main():
    removed = update_pages_json()
    removed_csv = update_rewritten_csv()
    upd, added = update_redirects()
    print(f"pages.json: removed {removed} research entries")
    print(f"rewritten-page-sources.csv: removed {removed_csv} rows")
    print(f"redirects.json: updated {upd}, added {added}")


if __name__ == "__main__":
    main()
