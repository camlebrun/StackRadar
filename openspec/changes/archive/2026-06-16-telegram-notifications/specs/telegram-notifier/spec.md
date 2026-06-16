## ADDED Requirements

### Requirement: Send message to a Telegram channel
The system SHALL send a text message to a specified Telegram channel or chat using the Telegram Bot API (`sendMessage` endpoint). The bot token and channel ID SHALL be passed as explicit parameters.

#### Scenario: Successful message send
- **WHEN** `send_notification(bot_token, channel_id, message)` is called with valid credentials and a non-empty message
- **THEN** the system POSTs to `https://api.telegram.org/bot<token>/sendMessage` with `chat_id` and `text`, and returns without error

#### Scenario: API failure is non-fatal
- **WHEN** the Telegram API returns a non-2xx status or a network error occurs
- **THEN** the system logs a warning with the error detail and returns without raising an exception

#### Scenario: Message too long is truncated
- **WHEN** the formatted message exceeds 4096 characters (Telegram API limit)
- **THEN** the message is truncated to 4096 characters before sending

### Requirement: Batch new releases into a single notification per channel
The system SHALL group all new releases for a single pipeline run into one message per channel, rather than sending one message per release, to avoid flooding channels.

#### Scenario: Multiple new releases in one run
- **WHEN** `notify_releases(bot_token, channel_id, records)` is called with a list of two or more release records
- **THEN** all releases are formatted into a single message and sent via one API call

#### Scenario: No new releases — no message sent
- **WHEN** `notify_releases` is called with an empty list
- **THEN** no API call is made and the function returns immediately

### Requirement: Format release messages in Telegram MarkdownV2
Each release entry in a notification message SHALL include: bold repo name, version tag, one-line summary, and a clickable URL. All dynamic content SHALL have MarkdownV2 reserved characters escaped before insertion.

#### Scenario: Release message formatting
- **WHEN** a release record with `repo`, `tag`, `analysis.summary`, and `html_url` is formatted
- **THEN** the output contains the repo name in bold, the version tag, a truncated summary (≤ 120 chars), and the URL as a hyperlink

#### Scenario: Special characters escaped
- **WHEN** a repo name or summary contains MarkdownV2 reserved characters (e.g., `.`, `-`, `(`, `)`, `!`)
- **THEN** each reserved character is prefixed with a backslash before the message is sent

### Requirement: Pipeline integration — notify after digest build
The `run_pipeline` function SHALL accept a `telegram_config` parameter (dict of `bot_token` + `channels`) and dispatch Telegram notifications at the end of each run for records with `fetched_at >= run_start`, after the email function call.

#### Scenario: Telegram notification dispatched for new records
- **WHEN** `run_pipeline` completes and new release records exist (fetched during this run)
- **THEN** `notify_releases` is called once per configured channel with the new records

#### Scenario: No Telegram config — skipped silently
- **WHEN** `telegram_config` is `None` or empty
- **THEN** no Telegram notification is attempted and pipeline execution continues normally
