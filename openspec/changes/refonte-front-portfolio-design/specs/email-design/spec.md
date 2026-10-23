## ADDED Requirements

### Requirement: Emails use the portfolio palette
The release digest, release card and error alert emails SHALL use the portfolio colours (page `#f5f0e8`, white cards with a `#e6d8c8` border and 16px radius, brown `#8d4f26` links and accents, heading `#1b2230`, body `#4f5d73`) and SHALL NOT contain the previous purple values or any gradient.

#### Scenario: No purple left
- **WHEN** a digest email is rendered
- **THEN** its HTML contains none of `#5b5fc7`, `#8b5cf6`, `#ede9fe`, `#f5f3ff` and no `linear-gradient`

### Requirement: Email-safe typography
Emails SHALL set headings in `'Playfair Display', Georgia, serif` and body text in `'DM Sans', Helvetica, Arial, sans-serif`, and SHALL NOT depend on a remote web font to stay readable. Styling SHALL be inline, and the emails SHALL keep declaring a light-only colour scheme.

#### Scenario: Web font blocked
- **WHEN** the mail client ignores web fonts
- **THEN** headings render in Georgia and body text in Helvetica or Arial

### Requirement: Email severity badges match the site
Severity badge colours in emails SHALL be the same background/text pairs as the site, each at least 4.5:1.

#### Scenario: Same palette
- **WHEN** a `high` release is rendered in an email
- **THEN** its badge uses `#f8e3cd` background and `#8a4300` text
