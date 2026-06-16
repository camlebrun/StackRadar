## MODIFIED Requirements

### Requirement: GCP docs anchor format
The system SHALL generate `html_url` anchors for GCP docs release notes using TitleCase month name, zero-padded day, and underscore separators (e.g. `#June_11_2026`), matching the format used by `docs.cloud.google.com`.

#### Scenario: Anchor for June 11 2026
- **WHEN** a GCP docs section header `## June 11, 2026` is parsed
- **THEN** `html_url` ends with `#June_11_2026`

#### Scenario: Anchor for October 01 2026
- **WHEN** a GCP docs section header `## October 01, 2026` is parsed
- **THEN** `html_url` ends with `#October_01_2026`

#### Scenario: Lakehouse base URL uses docs subdomain
- **WHEN** a Lakehouse release is fetched
- **THEN** `html_url` starts with `https://docs.cloud.google.com/lakehouse/docs/release-notes`
