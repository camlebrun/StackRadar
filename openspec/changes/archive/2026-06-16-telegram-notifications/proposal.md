## Why

The git-release project currently has no notification system, meaning contributors and maintainers have no real-time awareness of new releases, package updates, or pipeline events. Adding Telegram notifications enables teams to receive instant alerts in organized, purpose-specific channels without requiring any additional tooling on the recipient's side.

## What Changes

- Add a Telegram notification service that can send messages to multiple configurable channels
- Support distinct channel types (e.g., releases, errors, dbt-packages) so different audiences receive relevant updates
- Integrate notification dispatch into the existing Cloud Function pipeline (triggered on release events)
- Store Telegram bot token and channel IDs as environment secrets (not hardcoded)

## Capabilities

### New Capabilities

- `telegram-notifier`: Core notification service — wraps the Telegram Bot API, formats messages, and dispatches to one or more configured channels based on event type
- `telegram-channel-config`: Channel configuration layer — defines the mapping between event types (release, error, dbt-package update) and Telegram channel IDs, loaded from environment variables or a config file

### Modified Capabilities

<!-- No existing spec-level behavior changes -->

## Impact

- **Cloud Functions** (`functions/`): notification dispatch added to release processing logic
- **Environment config**: new secrets required — `TELEGRAM_BOT_TOKEN`, plus one `TELEGRAM_CHANNEL_<TYPE>` variable per channel
- **Dependencies**: adds `requests` (or `httpx`) for HTTP calls to the Telegram Bot API (likely already present)
- **No breaking changes** to existing release pipeline behavior — notifications are fire-and-forget side effects
