# Global Instructions For AI Agents

This is a running list of repo-wide instructions that future AI agents must preserve when editing this site.

## Site Header And Navigation

- Every public-facing page must keep the standard ALIUS site shell unless the user explicitly requests an exception.
- The standard shell includes the main logo header with `/assets/brand/alius-logo.svg` linked to `/`, followed by the primary tab navigation.
- The primary tabs must remain consistent across pages: Home, Team, Bulletin, Video Lectures, Events, Membership, Newsletter.
- Exactly one primary tab should be marked active with `id="active"`; subpages must keep their parent section active. For example, all Bulletin subpages, including tools and guidelines, keep the Bulletin tab active.
- Do not replace the main header, logo, or primary tabs with a page-specific mini navigation. Page-specific controls may appear below the shared site navigation.
- When a link opens a new page, tab, or tool route, that destination must still render with the same shared header/logo/tabs logic.
- Source files and generated `docs/` output must be kept in sync for any header/navigation change.

## Deployment

- After making website changes, push the committed changes to GitHub so the website deployment can update.
- Do not leave finished site edits only in the local working tree unless the user explicitly asks not to push.
- Commit and push only the files relevant to the requested change; preserve unrelated staged, unstaged, or untracked user work.
