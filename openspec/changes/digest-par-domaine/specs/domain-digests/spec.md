## ADDED Requirements

### Requirement: Per-domain digest files
The system SHALL write one digest file per domain on every pipeline run. A release belongs to the `dbt` domain when its `group` is `dbt-core`, `dbt-adapters`, `dbt-packages` or `orchestration`; to `gcp` when its `group` is `bigquery` or `lakehouse`; to `scaleway` when its `group` is `scaleway`. Security advisories SHALL be written to a `security` digest. Each file SHALL be named `digest-<domain>-<timestamp>.json` and use the same payload shape as the combined digest (`releases`, `advisories`).

#### Scenario: Releases are routed by group
- **WHEN** the pipeline builds digests for records with groups `dbt-adapters`, `bigquery` and `scaleway`
- **THEN** the `dbt` digest contains the dbt-adapters record, the `gcp` digest the bigquery record, and the `scaleway` digest the scaleway record, and no digest contains a record of another domain

#### Scenario: Unknown group
- **WHEN** a record has a `group` that maps to no domain
- **THEN** it SHALL still appear in the combined digest and SHALL NOT appear in any domain digest

### Requirement: Domain caps do not evict other domains
The system SHALL apply a record cap per domain, never a cap shared between domains. The `scaleway` digest SHALL be capped at 300 most recent records; the `dbt`, `gcp` and `security` digests SHALL be uncapped.

#### Scenario: Noisy domain does not hide dbt adapters
- **WHEN** R2 stores 338 Scaleway records and 27 dbt-adapter records
- **THEN** the `dbt` digest contains all 27 dbt-adapter records and the `scaleway` digest contains the 300 most recent Scaleway records

### Requirement: Manifest lists domain digests
`manifest.json` SHALL contain a `digests` object mapping each domain to its digest key, and SHALL keep the existing `digest` key pointing to the combined digest.

#### Scenario: Manifest after a run
- **WHEN** a pipeline run finishes
- **THEN** `manifest.json` contains `digest`, `digests.dbt`, `digests.gcp`, `digests.scaleway`, `digests.security` and `generated_at`

### Requirement: Cleanup keeps referenced digests
The system SHALL delete digest files that the new manifest does not reference, and SHALL NOT delete any file it references.

#### Scenario: Old digests removed
- **WHEN** a run writes new digests while older `digest-*.json` files exist
- **THEN** only files absent from the new manifest are deleted

### Requirement: Manifest carries tab counts
`manifest.json` SHALL contain a `counts` object with the exact number of `releases` (dbt, adapters and orchestration records), `packages` (distinct dbt-package repos), `bigquery`, `lakehouse`, `scaleway` and `advisories`, computed from every stored record, not from a capped digest.

#### Scenario: Counts ignore caps
- **WHEN** R2 stores 338 Scaleway records
- **THEN** `counts.scaleway` is 338 although the `scaleway` digest holds 300
