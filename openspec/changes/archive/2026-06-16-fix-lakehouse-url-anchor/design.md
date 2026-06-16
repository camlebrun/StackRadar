## Context

`fetch_gcp_docs_releases` in `src/fetcher.py` is shared by BigQuery and Lakehouse. It parses date-section headers (`## June 11, 2026`) and builds `html_url` by appending an anchor to `docs_base_url`. Line 344 generates the anchor as:

```python
anchor = dt.strftime("%B-%d-%Y").lower()   # → june-11-2026
```

The real GCP Lakehouse anchor format is `#June_11_2026` — month in TitleCase, zero-padded day, underscore separators. Additionally `repos.json` has the wrong base domain for Lakehouse (`cloud.google.com` instead of `docs.cloud.google.com`).

Existing records stored in R2 carry both wrong values and need a one-time patch.

## Goals / Non-Goals

**Goals:**
- Fix anchor generation for all future GCP docs records (Lakehouse + BigQuery)
- Fix Lakehouse `docs_base_url` in `repos.json`
- Patch `html_url` on all existing Lakehouse records already in R2

**Non-Goals:**
- Changing any other field on existing records
- Re-running LLM analysis on existing records
- Changing BigQuery `docs_base_url` (domain is correct for BigQuery)

## Decisions

### 1. Fix anchor format globally in `fetch_gcp_docs_releases`

Change line 344 from:
```python
anchor = dt.strftime("%B-%d-%Y").lower()
```
to:
```python
anchor = dt.strftime("%B_%d_%Y")
```

`%B` produces TitleCase month (`June`), `%d` produces zero-padded day (`11`), underscores match the GCP docs format. This fix applies to both BigQuery and Lakehouse — BigQuery uses the same docs anchor format.

**Why not a per-source parameter:** Both sources share the same format; adding a parameter would be premature complexity.

### 2. Fix Lakehouse `docs_base_url` in `repos.json`

Change:
```
"docs_base_url": "https://cloud.google.com/lakehouse/docs/release-notes"
```
to:
```
"docs_base_url": "https://docs.cloud.google.com/lakehouse/docs/release-notes"
```

BigQuery's `docs_base_url` stays on `cloud.google.com` — only Lakehouse moved to `docs.cloud.google.com`.

### 3. Backfill script to patch existing R2 records

A local script (`scripts/local/backfill_gcp_urls.py`) that:
1. Lists all release objects in R2 under `releases/google/` prefix
2. For each record where `group` is `lakehouse` or `bigquery`, recomputes the correct `html_url` from `published_at` and the fixed `docs_base_url`
3. Writes the patched record back to R2 (only if `html_url` changed)

**Why a script and not pipeline re-run:** Re-running the pipeline would skip existing records (`release_exists` check). A targeted patch script is surgical and auditable.

## Risks / Trade-offs

- **BigQuery anchors** — assumed to follow the same `#Month_DD_YYYY` format. If they differ, BigQuery links would break. → Mitigation: verify one BigQuery URL manually before running backfill.
- **Backfill overwrites in-place** — no rollback beyond restoring from a local backup. → Mitigation: script prints a dry-run diff before writing.

## Migration Plan

1. Fix `fetcher.py` line 344
2. Fix `repos.json` Lakehouse `docs_base_url`
3. Run `scripts/local/backfill_gcp_urls.py --dry-run` to preview changes
4. Run without `--dry-run` to apply
5. Deploy updated code via existing CI/CD
