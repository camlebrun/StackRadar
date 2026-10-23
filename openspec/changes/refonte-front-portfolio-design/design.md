## Context

The front is six static pages (`/`, `/security`, `/dbt-packages`, `/bigquery`, `/lakehouse`, `/scaleway`) built by Vite, in plain JS and a 1,100-line `style.css` with a purple theme. Each page fetches `manifest.json` then the whole digest (742 KB). Helpers were recently extracted into `public/common.js`. The portfolio (`camlebrun.github.io`, Astro + Tailwind) uses a warm editorial palette with Playfair Display and DM Sans, white rounded cards, pill buttons, and no dark mode.

## Goals / Non-Goals

**Goals:**
- Visually consistent with the portfolio.
- Shareable, reload-safe filter state.
- `dbt-core` readable at a glance (4 minors instead of 32 cards).
- Less duplicated code across pages.

**Non-Goals:**
- A framework (React, Astro, Tailwind) or an SPA router.
- A dark theme.
- Changing what the pipeline stores (see `digest-par-domaine`).
- Redesigning the Security page's advisory logic.

## Decisions

1. **Keep six pages and plain ES modules.** The site is small, static and cheap to host; a framework would add a build and a dependency for little gain. An SPA would speed tab switches, but with one small digest per domain (cached `immutable`) a page switch costs one cached request. Alternative considered: Astro like the portfolio; rejected because sharing the look only needs sharing tokens, not the toolchain.
2. **Share the look through CSS custom properties copied from the portfolio**, not through a shared package. Two repos, one author; a copy of ~10 variables is simpler than publishing a package, and the portfolio's own `CHANGELOG-REFONTE.md` shows its tokens are stable.
3. **Data access in one module (`common.js` → `loadDomain(name)`).** It fetches `manifest.json` (no-store), picks `manifest.digests[name]` and falls back to `manifest.digest` filtered client-side. The fallback lets the redesign deploy before or after `digest-par-domaine` with no ordering constraint.
4. **URL state with `URLSearchParams` and `history.replaceState`.** `replaceState` keeps the back button useful (no history entry per chip click). Defaults are omitted so the canonical URL stays `/`; "all severities" is the exception because it differs from the default and must survive a reload.
5. **Group dbt-core in the client, not in the pipeline.** Grouping is a presentation concern and the digest already carries `tag` and `analysis.severity`. Row severity is the maximum of the group's releases; threshold-hidden releases are counted rather than silently dropped, so a collapsed row never lies about its contents.
6. **Warm severity palette**, chosen for contrast on beige rather than for hue fidelity: critical rust-red, high ochre-orange, medium amber on cream, low sage, none grey. Exact values are fixed during implementation with a contrast script (≥ 4.5:1 per badge).
7. **Fonts via the same Google Fonts URL as the portfolio**, with `font-display: swap` and system fallbacks so a blocked request never hides text.

8. **Emails get the same tokens, but fallback fonts first.** Most mail clients ignore web fonts, so headings are `Playfair Display, Georgia` and body `DM Sans, Helvetica, Arial`, all styling inline (the existing approach). The severity pairs are duplicated in `functions/email/main.py` because the Cloud Function ships separately from `public/`; a comment names the source so the two stay in step.

## Risks / Trade-offs

- [Playfair/DM Sans add a third-party request and a layout shift] → `font-display: swap`, fallback stacks sized close to the web fonts.
- [Medium+ default hides `low` releases on every release page, which some visitors may miss] → the select states "Medium and above" and the URL `?sev=all` is linkable.
- [Grouping hides patches behind a click] → row shows the max severity and a "+N hidden" count, and the expanded list is keyboard accessible.
- [Rewriting `style.css` can regress the five untouched pages] → migrate page by page behind tokens, check each page at 375 px and 1280 px (the mobile overflow fix in #56 must not regress).
- [Email clients render colours and fonts differently] → keep inline styles and light-only scheme, check the HTML in a browser and with a test send before shipping.
- [Portfolio tokens drift] → tokens are copied with a comment naming the source file.

## Migration Plan

1. Land tokens and the shared data/URL modules; verify the release page.
2. Migrate remaining pages one per commit.
3. After `digest-par-domaine` is deployed and verified, drop the manifest fallback in a later cleanup.
Rollback: revert the page's commit; each page is independent of the others once `common.js` is stable.

## Open Questions

- Should the Security page keep its own severity vocabulary (`patch-now` / `patch-soon`) or reuse the badge palette? Defaulting to reuse the palette.
- Gzip for `r2.dev` responses is out of scope here (see `digest-par-domaine`).
