## ADDED Requirements

### Requirement: Filters are mirrored in the URL
The release page SHALL read `sev`, `group`, `repo` and `q` from the query string on load and SHALL update the query string with `history.replaceState` whenever a filter changes. A parameter at its default value SHALL be omitted, except that choosing all severities SHALL be written as `sev=all`.

#### Scenario: Shareable view
- **WHEN** a visitor opens `/?group=dbt-v2&sev=high`
- **THEN** the `dbt v2` chip is active, the severity select shows "High and above", and only matching cards are visible

#### Scenario: Default state
- **WHEN** a visitor opens `/` with no query string
- **THEN** severity is Medium and above and the URL stays `/`

#### Scenario: Changing a filter
- **WHEN** a visitor selects "All severities"
- **THEN** the URL becomes `/?sev=all` without adding a history entry

### Requirement: Invalid parameters are ignored
Unknown or malformed parameter values SHALL fall back to the default and SHALL NOT raise an error.

#### Scenario: Bad severity
- **WHEN** the URL is `/?sev=banana`
- **THEN** severity is Medium and above
