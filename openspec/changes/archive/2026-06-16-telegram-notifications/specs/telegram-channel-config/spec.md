## ADDED Requirements

### Requirement: Load Telegram bot token from GCP Secret Manager
The system SHALL retrieve the Telegram bot token from GCP Secret Manager using the key `TELEGRAM_BOT_TOKEN`, following the same pattern as existing secrets (`GITHUB_TOKEN`, `EMAIL_FUNCTION_URL`).

#### Scenario: Bot token available
- **WHEN** `get_secret(GCP_PROJECT, "TELEGRAM_BOT_TOKEN")` resolves successfully
- **THEN** the token is passed into `run_pipeline` as part of `telegram_config`

#### Scenario: Bot token missing — Telegram disabled
- **WHEN** `get_secret(GCP_PROJECT, "TELEGRAM_BOT_TOKEN")` raises an exception
- **THEN** the system logs a warning ("TELEGRAM_BOT_TOKEN not in Secret Manager — Telegram notifications disabled") and `telegram_config` is set to `None`

### Requirement: Load one channel ID per event type from Secret Manager
The system SHALL support multiple named Telegram channels, each identified by a dedicated secret: `TELEGRAM_CHANNEL_RELEASES`, `TELEGRAM_CHANNEL_ERRORS`, `TELEGRAM_CHANNEL_DBT_PACKAGES`. Each channel is optional; missing channels are skipped silently.

#### Scenario: Releases channel configured
- **WHEN** `TELEGRAM_CHANNEL_RELEASES` is present in Secret Manager
- **THEN** new release records are dispatched to that channel ID

#### Scenario: Errors channel configured
- **WHEN** `TELEGRAM_CHANNEL_ERRORS` is present and a repo fails during pipeline execution
- **THEN** a failure notification is sent to the errors channel

#### Scenario: dbt-packages channel configured
- **WHEN** `TELEGRAM_CHANNEL_DBT_PACKAGES` is present
- **THEN** new dbt-package release records are dispatched to that channel instead of (or in addition to) the releases channel

#### Scenario: A channel secret is missing — that channel skipped
- **WHEN** `get_secret` for a specific channel ID raises an exception
- **THEN** a warning is logged and no notification is sent to that channel; other configured channels are unaffected

### Requirement: Channel config passed as structured dict to run_pipeline
The assembled channel configuration SHALL be passed to `run_pipeline` as a `telegram_config` dict with keys `bot_token` (str) and `channels` (dict mapping channel name to channel ID string).

#### Scenario: Full config structure
- **WHEN** bot token and at least one channel ID are available
- **THEN** `telegram_config` is `{"bot_token": "<token>", "channels": {"releases": "<id>", ...}}`

#### Scenario: Empty channels dict
- **WHEN** bot token is available but no channel secrets resolve
- **THEN** `telegram_config` is `{"bot_token": "<token>", "channels": {}}` and no notifications are sent (no channels to route to)
