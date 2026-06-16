## ADDED Requirements

### Requirement: Single canonical repos.json loader
`load_repos()` in `pipeline.py` SHALL be the single canonical function for loading and normalising `repos.json`. `digest.py` SHALL import and reuse `load_repos()` instead of defining its own `_load_repo_overrides()` that rereads the same file.

#### Scenario: Digest uses pipeline loader
- **WHEN** `digest.py` needs repo override data (deprecated, notice fields)
- **THEN** it SHALL call `load_repos()` from `pipeline` and derive the override map from the returned list, not reread `repos.json` independently

#### Scenario: Deprecated fields available via load_repos
- **WHEN** a repo entry in `repos.json` has `deprecated: true` or `notice` fields
- **THEN** `load_repos()` SHALL preserve those fields in the returned dict so callers can derive any override map they need

### Requirement: Advisory cursor key helper
`store.py` SHALL define a private helper `_advisory_cursor_key(owner, repo)` returning `f"meta/advisory-cursor/{owner}/{repo}.json"`. Both `get_advisory_cursor` and `set_advisory_cursor` SHALL use this helper.

#### Scenario: Consistent key generation
- **WHEN** `get_advisory_cursor` or `set_advisory_cursor` is called
- **THEN** the storage key SHALL be produced by `_advisory_cursor_key`, not by an inlined f-string

### Requirement: Unified GitHub headers helper
`fetcher.py` SHALL expose a single `_github_headers(token, *, accept)` function replacing `_headers_base` and `_headers`. `security_advisories.py` SHALL import this helper instead of building its own headers dict.

#### Scenario: Default Accept header
- **WHEN** `_github_headers` is called without an explicit `accept` argument
- **THEN** it SHALL return headers with `Accept: application/vnd.github+json`

#### Scenario: Custom Accept header for raw content
- **WHEN** `_github_headers` is called with `accept="application/vnd.github.raw+json"`
- **THEN** it SHALL return headers with that Accept value
