"""Disable broken Weebly forms that POST to `//www.weebly.com/weebly/apps/formSubmit.php`.

The endpoint is dead — submissions go into a void. Rather than leave a fake
"subscribe" button, strip the form wrapper and replace it with a static
note directing users to the ALIUS contact address.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

ROOTS = [
    REPO / "site-src" / "content",
    REPO / "docs",
]

# Match a whole <form ... action="...formSubmit.php..."> ... </form>
FORM_RE = re.compile(
    r'<form\b[^>]*action\s*=\s*["\'][^"\']*formSubmit\.php[^"\']*["\'][^>]*>[\s\S]*?</form>',
    re.IGNORECASE,
)

REPLACEMENT = (
    '<div class="paragraph" style="text-align:center;">'
    '<em>Contact us at <a href="mailto:contact@aliusresearch.org">contact@aliusresearch.org</a> '
    'for inquiries or to join the mailing list.</em>'
    '</div>'
)


def main():
    files = changed = hits = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.html"):
            files += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            new, n = FORM_RE.subn(REPLACEMENT, text)
            if n:
                path.write_text(new, encoding="utf-8")
                changed += 1
                hits += n
    print(f"Scanned {files}, changed {changed}, stripped {hits} broken Weebly forms")


if __name__ == "__main__":
    main()
