"""Remove unused Weebly runtime artifacts from every content file.

Targets:
  A16 · <script src="…main-customer-accounts-site.js"> and the
        <div id="customer-accounts-app"> div. No customer/store exists.
  A23 · <a href=""><img … sitename logo …></a> — fix empty href to "/".
  A16b · inline <script>…_W.CustomerAccounts.RPC…</script> and initCustomerAccountsModels.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOTS = [
    REPO / "site-src" / "content",
    REPO / "site-src" / "partials",
    REPO / "docs",
]

PATTERNS = [
    # <script src="...main-customer-accounts-site.js"></script>
    (re.compile(
        r'<script\b[^>]*src\s*=\s*["\'][^"\']*main-customer-accounts-site\.js[^"\']*["\'][^>]*>\s*</script>\s*',
        re.IGNORECASE | re.DOTALL,
    ), ""),
    # <div id="customer-accounts-app"></div>
    (re.compile(
        r'<div\s+id\s*=\s*["\']customer-accounts-app["\']\s*>\s*</div>\s*',
        re.IGNORECASE | re.DOTALL,
    ), ""),
    # Full initCustomerAccountsModels IIFE block
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*function\s+initCustomerAccountsModels\s*\(\)\s*\{.*?</script>\s*',
        re.IGNORECASE | re.DOTALL,
    ), ""),
    # A16 · Inline _W.CustomerAccounts.RPC setup blobs (`<script> (function()
    # { _W.setup_rpc({...}); _W.setup_model_rpc({...}) })(); </script>` and
    # similar). These were the JSON payloads feeding the customer-accounts
    # runtime we already removed.
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*\(function\s*\(\)\s*\{\s*_W\.setup_rpc\b[\s\S]*?</script>\s*',
        re.IGNORECASE,
    ), ""),
    # A16 · Store-config blobs: <script>_W = _W || {}; _W.customerLocale = …;
    #                                   com_currentSite = "…"; com_userID = "…";</script>
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*_W\s*=\s*_W\s*\|\|\s*\{\};[\s\S]*?com_userID\s*=\s*"[^"]*";?\s*</script>\s*',
        re.IGNORECASE,
    ), ""),
    # A16 · The trivial `<script> _W = _W || {}; _W.securePrefix='UNSET';</script>`
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*_W\s*=\s*_W\s*\|\|\s*\{\};\s*_W\.securePrefix\s*=\s*["\'][^"\']*["\']\s*;\s*</script>\s*',
        re.IGNORECASE,
    ), ""),
    # A16 · Pair of Weebly globals sometimes on their own line:
    # `<script> _W.themePlugins = [];</script>` and `_W.recaptchaUrl = …`
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*_W\.themePlugins\s*=\s*\[\];\s*</script>\s*',
        re.IGNORECASE,
    ), ""),
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*_W\.recaptchaUrl\s*=\s*["\'][^"\']*["\']\s*;\s*</script>\s*',
        re.IGNORECASE,
    ), ""),
    # A16 · `<script>_W.relinquish && _W.relinquish()</script>`
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*_W\.relinquish\s*&&\s*_W\.relinquish\(\)\s*;?\s*</script>\s*',
        re.IGNORECASE,
    ), ""),
    # A16 · Remaining `<script>_W.configDomain = "www.weebly.com";</script>`
    (re.compile(
        r'<script\b(?![^>]*src=)[^>]*>\s*_W\.configDomain\s*=\s*["\']www\.weebly\.com["\']\s*;\s*</script>\s*',
        re.IGNORECASE,
    ), ""),
    # Empty sitename href — <a href=""><img ... 1477332210 ..>
    (re.compile(
        r'<a\s+href\s*=\s*""\s*>(\s*<img[^>]*1477332210[^>]*>\s*)</a>',
        re.IGNORECASE | re.DOTALL,
    ), r'<a href="/" aria-label="ALIUS home">\1</a>'),
    # Also catch the plain empty href wrapping any img in the sitename block
    (re.compile(
        r'<span class="wsite-logo">\s*<a\s+href\s*=\s*""\s*>',
        re.IGNORECASE | re.DOTALL,
    ), '<span class="wsite-logo"><a href="/" aria-label="ALIUS home">'),
]


def process(text: str) -> tuple[str, int]:
    total = 0
    new = text
    for pat, repl in PATTERNS:
        new, n = pat.subn(repl, new)
        total += n
    return new, total


def main():
    total_files = changed = hits = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in (".html", ".raw.html"):
                continue
            # also catch .raw.html via endswith
            if path.suffix.lower() == ".html" or path.name.endswith(".raw.html"):
                pass
            total_files += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            new, n = process(text)
            if n > 0:
                path.write_text(new, encoding="utf-8")
                changed += 1
                hits += n
    print(f"Scanned: {total_files} files")
    print(f"Changed: {changed} files")
    print(f"Removals/fixes: {hits}")


if __name__ == "__main__":
    main()
