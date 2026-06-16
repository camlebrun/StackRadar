## 1. Code Fix

- [x] 1.1 In `src/fetcher.py` line 344, change `dt.strftime("%B-%d-%Y").lower()` to `dt.strftime("%B_%d_%Y")`
- [x] 1.2 In `repos.json`, update Lakehouse `docs_base_url` from `https://cloud.google.com/lakehouse/docs/release-notes` to `https://docs.cloud.google.com/lakehouse/docs/release-notes`

## 2. Tests

- [x] 2.1 Update existing GCP docs fetcher tests to assert `html_url` contains `#June_11_2026` format (underscore, TitleCase)
- [x] 2.2 Add a test case for the October edge case (`#October_01_2026`) to confirm zero-padding is preserved
- [x] 2.3 Run `pytest tests/test_fetcher.py -v` — all tests pass

## 3. Backfill Script

- [x] 3.1 Create `scripts/local/backfill_gcp_urls.py` that lists all objects under `releases/google/` in R2, reads each JSON, recomputes `html_url` from `published_at` using the corrected format, and prints or writes the diff
- [x] 3.2 Add `--dry-run` flag (default: dry-run) and `--apply` flag to write changes
- [x] 3.3 Run `python scripts/local/backfill_gcp_urls.py --dry-run` — review the diff output
- [x] 3.4 Verify at least one corrected URL resolves (manual browser check: `https://docs.cloud.google.com/lakehouse/docs/release-notes#June_11_2026`)
- [x] 3.5 Run `python scripts/local/backfill_gcp_urls.py --apply` to patch R2

## 4. Validation

- [x] 4.1 Run full test suite `pytest` — all pass
- [x] 4.2 Run `ruff check src tests && black --check src tests && mypy --strict src` — all clean
