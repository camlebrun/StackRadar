## ADDED Requirements

### Requirement: dbt-core grouped by minor version
When the `dbt core` or `dbt v2` group is active, the release page SHALL show one row per `major.minor` instead of one card per release. The row SHALL display the minor label, the number of releases, the date of the latest release, and the highest severity among them.

#### Scenario: One row per minor
- **WHEN** the `dbt-core` records are v1.10.0, v1.11.0–v1.11.16, v1.12.0–v1.12.6 and v2.0.0–v2.0.8
- **THEN** four rows are shown: `v2.0`, `v1.12`, `v1.11`, `v1.10`, newest first

### Requirement: Patches are collapsed
Each row SHALL list its releases collapsed by default and expand on activation, using a keyboard-accessible control. Releases below the active severity threshold SHALL stay hidden and be counted ("+N hidden").

#### Scenario: Expanding a minor
- **WHEN** the visitor activates the `v1.11` row
- **THEN** its releases at or above the severity threshold are listed with their tag, date and severity

#### Scenario: Threshold hides low patches
- **WHEN** severity is Medium and above and 12 of 17 `v1.11` releases are `low` or `none`
- **THEN** the row shows "+12 hidden" and the expanded list contains 5 releases

### Requirement: Chip scope
The `dbt core` chip SHALL cover `dbt-core` releases with major version 1 and the `dbt v2` chip those with major version 2.

#### Scenario: dbt v2 chip
- **WHEN** the `dbt v2` chip is active
- **THEN** only `v2.x` rows are shown
