## Why

StackRadar's front uses a purple look that does not match the owner's portfolio (warm beige/brown, Playfair Display + DM Sans). Filter state is lost on every page change or reload, and the 32 `dbt-core` releases are shown as a flat list of cards, which buries the few that matter. The six pages also repeat the same data loading and UI code.

## What Changes

- Restyle every page with the portfolio's design tokens: beige background, brown primary, navy headings, sage accent, white rounded cards, pill buttons, Playfair Display + DM Sans, no dark theme.
- Replace the purple palette and severity colours with a warm palette that keeps text contrast at WCAG AA on the beige background.
- Add a shared data module that loads `manifest.json` then the page's domain digest (`manifest.digests.<domain>`), falling back to `manifest.digest` while the domain digests are not yet deployed.
- Store filter state (severity, group, repo, search) in the URL query string so views are shareable and survive reloads.
- Group `dbt-core` releases by minor version (`v2.0`, `v1.12`, `v1.11`, `v1.10`): one row per minor, highest severity shown, patches collapsed beneath it.
- Keep the group chips `All · dbt core · dbt v2 · dbt-adapters · Orchestration` (`dbt core` = v1.x) and the Medium-and-above default severity.
- Restyle the notification emails (`functions/email`) with the same tokens and severity palette, using email-safe fallback fonts.
- Keep the six separate pages and plain ES modules; no framework, no build-step change beyond the existing Vite config.

## Capabilities

### New Capabilities
- `front-design`: portfolio-aligned visual system (tokens, fonts, cards, buttons, severity palette, no dark theme).
- `filter-url-state`: filter state read from and written to the URL query string.
- `dbt-core-minor-grouping`: `dbt-core` releases grouped by minor version with collapsed patches.
- `email-design`: release digest and alert emails styled like the portfolio.

### Modified Capabilities

## Impact

- Code: `functions/email/templates/*.html` and `functions/email/main.py` (severity colours, error email), `public/style.css` (rewritten around tokens), `public/common.js` (data + URL helpers), the six `public/*/app.js` and `index.html`, `vite.config.js` unchanged.
- Dependencies: Google Fonts stylesheet (Playfair Display, DM Sans), same source as the portfolio. No npm dependency added.
- Depends on: `digest-par-domaine` for per-domain digests; works without it through the fallback.
- Cost: none (static hosting unchanged).
