## ADDED Requirements

### Requirement: Backfill script patches existing GCP records in R2
The system SHALL provide a local script that rewrites `html_url` on all existing Lakehouse and BigQuery records in R2 to the corrected anchor format, without modifying any other field.

#### Scenario: Dry-run shows diff without writing
- **WHEN** `backfill_gcp_urls.py --dry-run` is run
- **THEN** the script prints each record that would be changed (old URL → new URL) and exits without writing to R2

#### Scenario: Apply mode patches only changed records
- **WHEN** `backfill_gcp_urls.py` is run without `--dry-run`
- **THEN** only records whose `html_url` differs from the recomputed value are written back to R2

#### Scenario: Records with correct URL are skipped
- **WHEN** a record already has the correct `html_url`
- **THEN** the script skips it and does not write to R2

#### Scenario: Non-GCP records are untouched
- **WHEN** the script iterates R2 objects
- **THEN** only records under `releases/google/` with `group` in `["lakehouse", "bigquery"]` are considered
