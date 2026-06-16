## Why

The `html_url` field for Google Cloud Lakehouse release notes records contains broken anchors. The fetcher generates `#june-11-2026` (lowercase, hyphen-separated) but the actual GCP docs use `#June_11_2026` (TitleCase, underscore-separated). Additionally the Lakehouse base URL domain is wrong (`cloud.google.com` instead of `docs.cloud.google.com`). As a result every Lakehouse release link in the digest is a 404, and existing stored records in R2 carry the wrong URL.

## What Changes

- Fix anchor generation in `src/fetcher.py`: `%B-%d-%Y` lowercased → `%B_%d_%Y` (TitleCase, underscores)
- Fix Lakehouse `docs_base_url` in `repos.json`: `https://cloud.google.com/lakehouse/docs/release-notes` → `https://docs.cloud.google.com/lakehouse/docs/release-notes`
- Add a backfill script that patches `html_url` on all existing Lakehouse records in R2 to the correct format
- Verify BigQuery anchor format is unaffected (or fix if needed)

## Capabilities

### New Capabilities

- `gcp-url-backfill`: One-shot script to rewrite `html_url` on all existing GCP-sourced records in R2 with the corrected anchor format

### Modified Capabilities

- `gcp-docs-fetcher`: Anchor format fix in `fetch_gcp_docs_releases` — changes `html_url` generation for all future GCP docs records

## Impact

- **`src/fetcher.py`** line 344: anchor format change affects BigQuery and Lakehouse (both use `fetch_gcp_docs_releases`)
- **`repos.json`**: Lakehouse `docs_base_url` domain correction
- **R2 storage**: existing Lakehouse records need `html_url` patched via backfill script
- **No manifest or API changes** — `html_url` is a display field only, no downstream logic depends on its exact format
