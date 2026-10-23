## Why

`get_digest` keeps only the 500 most recent releases across every source. Scaleway alone stores 338 entries, so older but valid releases are evicted: only 3 of the 27 stored dbt-adapter releases and 46 of the 130 dbt-package releases reach the frontend. Every page also downloads the full 742 KB digest to use a slice of it.

## What Changes

- The pipeline writes one digest per domain (`dbt`, `gcp`, `scaleway`, `security`) next to the existing combined digest, each with its own cap, so a noisy source can no longer evict another.
- `manifest.json` gains a `digests` map (`{"dbt": "digest-dbt-<ts>.json", ...}`). The existing `digest` key is kept unchanged so the deployed frontend keeps working until the redesign ships.
- Stale digest cleanup keeps every file referenced by the manifest.
- Per-domain caps live in `src/config.py`; only Scaleway gets a cap, the other domains are uncapped.
- The combined digest and its 500 cap are untouched in this change. **No BREAKING change.**

## Capabilities

### New Capabilities
- `domain-digests`: per-domain digest files, their manifest entry, caps, and cleanup.

### Modified Capabilities

## Impact

- Code: `src/store.py` (`write_digest_json`), `src/pipeline.py` (`_build_and_clean_digest`), `src/config.py`, `tests/test_store.py`, `tests/test_pipeline.py`.
- Data: new objects `digest-<domain>-<ts>.json` in the R2 bucket; one extra write per domain per run (4 small PUTs).
- Cost: negligible (R2 storage and class A operations stay within free tier).
- Frontend: none; the redesign change consumes `manifest.digests`.
