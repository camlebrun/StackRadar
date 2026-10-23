## 1. Design tokens

- [x] 1.1 Define the `:root` tokens in `public/style.css` (colours, radii, fonts) with a comment citing the portfolio source
- [x] 1.2 Pick severity colours and verify each pair reaches 4.5:1 with a small contrast script
- [x] 1.3 Add the Google Fonts link (Playfair Display, DM Sans) with `display=swap` to every page and set fallback stacks
- [x] 1.4 Restyle header, tabs, chips (pill), cards (white, 1rem), drawer and footer from the tokens; remove purple values and `prefers-color-scheme` rules

## 2. Shared modules

- [ ] 2.1 Add `loadDomain(name)` to `public/common.js` with the `manifest.digest` fallback
- [ ] 2.2 Add `readFilters()` / `writeFilters()` URL helpers with validation and default omission
- [ ] 2.3 Add a small pure `groupByMinor(records)` helper (max severity, counts, latest date)

## 3. Release page

- [ ] 3.1 Load the `dbt` domain through `loadDomain` and restore filters from the URL on load
- [ ] 3.2 Write filters to the URL on every change (`replaceState`)
- [ ] 3.3 Render `dbt-core` as minor rows with collapsed patches, "+N hidden" and keyboard-accessible expansion
- [ ] 3.4 Keep chips `All · dbt core · dbt v2 · dbt-adapters · Orchestration` and the Medium-and-above default

## 4. Other pages

- [ ] 4.1 Migrate `/security` to the tokens and `loadDomain('security')`
- [ ] 4.2 Migrate `/dbt-packages` to the tokens and `loadDomain('dbt')`
- [ ] 4.3 Migrate `/bigquery` and `/lakehouse` to the tokens and `loadDomain('gcp')`
- [ ] 4.4 Migrate `/scaleway` to the tokens and `loadDomain('scaleway')`

## 5. Verification

- [ ] 5.1 `npx vite build` passes
- [ ] 5.2 Check every page at 375 px and 1280 px for horizontal overflow and contrast
- [ ] 5.3 Test URL scenarios: default, `?group=dbt-v2&sev=high`, `?sev=banana`, `?sev=all` after reload
- [ ] 5.4 Check the page works with the fallback (no `digests` in manifest) and with domain digests
