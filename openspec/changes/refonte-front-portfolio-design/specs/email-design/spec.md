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

### Requirement: Email card mirrors the site card
Each release in an email SHALL use the same structure as a site card: repo label (display name as on the site), severity pill, serif title (`name`, falling back to `tag`), date, summary, up to 3 key changes, up to 3 tags (without `pre-release`), and a link to the release. Text from releases SHALL be HTML-escaped.

#### Scenario: Card content
- **WHEN** a release named `dbt-core v2.0.5` with 4 key changes and tags `bug-fix`, `pre-release`, `config-change` is rendered
- **THEN** the card shows that title, the formatted date, 3 key changes and the tags `bug-fix` and `config-change`

#### Scenario: Untrusted markup
- **WHEN** a summary contains `<script>`
- **THEN** the email contains `&lt;script&gt;` and no `<script>` element
