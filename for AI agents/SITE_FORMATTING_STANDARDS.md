# Site Formatting Standards For AI Agents

This is the running inventory of site-wide formatting practices for ALIUS. Future agents should update this file when a formatting decision becomes reusable across pages.

## Source Of Truth

- Use `Shared/assets/css/alius-redesign.css` for global layout, typography, navigation, anchor, and responsive standards.
- Use `Shared/assets/js/alius-redesign.js` for generated page anchors and shared interactive formatting behavior.
- Keep the generated `docs/` copies synchronized after source changes. For shared assets, `docs/assets/shared/...` must match `Shared/assets/...`.
- Do not introduce one-off page CSS when a rule is a reusable layout standard. Add a token or shared selector instead.
- Redirect-only pages may stay minimal, but every rendered public content page should use the shared site shell.

## Global Layout Measures

- Long-form prose uses `--alius-prose-measure: 68ch` with responsive gutters from `--alius-prose-gutter`.
- Page titles use `--alius-title-measure: 760px` unless the title belongs to a tool, card, or intentionally wide feature.
- Standard content bands use `--alius-content-measure: 920px`; wide index/tool layouts may use `--alius-wide-measure: 1064px` or a local wider container only when the content requires scanning across cards or controls.
- Page sections should use stable semantic IDs and consistent vertical rhythm. Prefer section IDs that name the content, such as `membership-overview`, `newsletter-signup`, or `interview-generator`.
- Text boxes, cards, and controls must use `box-sizing: border-box`, `min-width: 0`, and responsive `max-width` constraints so long labels and narrow screens cannot cause horizontal overflow.

## Navigation And Anchors

- Primary navigation order is always: Home, Team, Bulletin, Video Lectures, Events, Membership, Newsletter.
- Exactly one primary nav item is active with `id="active"`; subpages keep the parent tab active.
- The primary navigation remains sticky at the top. Do not replace it with page-specific navigation.
- The canonical subsection navigation is generated `.alius-anchor-nav`: fixed side anchors on desktop, horizontal anchors on tablet/mobile.
- Do not add new fixed bottom `.section-nav` bars. Legacy `.section-nav` markup is deprecated and should be removed when touching a core page.
- Anchor targets must account for sticky navigation and mobile wrapping. Use shared scroll-margin rules instead of page-specific magic numbers.

## Responsive Standards

- Tablet and phone layouts must not depend on fixed pixel widths. Use `clamp()`, `min()`, fluid grid tracks, and single-column fallbacks.
- Mobile controls should preserve at least a 34-40px touch target where practical.
- Respect `env(safe-area-inset-*)` for sticky or edge-adjacent navigation.
- Cards and repeated content should collapse before text becomes cramped. Two-column grids should become one column around the existing 720px breakpoint unless the component has a more specific reason.
- Avoid horizontal overflow on all core pages. If a component scrolls horizontally by design, hide scrollbars only when touch and keyboard access remain usable.

## Core Page Expectations

- Core pages are Home, About redirect, Team, Bulletin, Bulletin guidelines/tools, Video Lectures, Events, Membership, and Newsletter.
- Rendered core pages should load `/assets/shared/css/alius-redesign.css` and `/assets/shared/js/alius-redesign.js`.
- Bulletin and tool pages may keep specialized CSS for forms, PDFs, or publication previews, but global shell, menu, anchor, and responsive behavior should still come from shared assets.
- Event, Bulletin, Membership, Newsletter, and Video Lecture indexes should expose stable high-level anchor IDs rather than relying on generated headings alone.

## QA Checklist

- Rebuild or mirror `docs/` after source changes.
- Check desktop, tablet, and phone widths for `/`, `/bulletin/`, `/events/`, `/membership/`, `/video-lectures/`, and `/bulletin/instructions-guidelines/`.
- Confirm there is no horizontal overflow, clipped nav label, hidden final section, or mismatch between source and generated shared assets.
- Confirm `#` links land below the sticky nav and that the active primary tab is correct.
