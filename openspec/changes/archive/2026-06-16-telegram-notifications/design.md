## Context

The git-release pipeline (GCP Cloud Run Job) fetches GitHub/GCP releases, LLM-analyses them, stores results in Cloudflare R2, and already dispatches email notifications via `_call_email_function` at the end of `run_pipeline`. Secrets are managed via GCP Secret Manager and accessed with `get_secret(GCP_PROJECT, "KEY_NAME")`.

The project needs a parallel notification channel: Telegram, sending messages to distinct channels (e.g., new releases, pipeline errors, dbt-package updates) so different audiences receive only the alerts relevant to them.

## Goals / Non-Goals

**Goals:**
- Implement a `TelegramNotifier` module in `src/` that posts formatted messages to one or more configured channels via the Telegram Bot API
- Support multiple named channels, each with a distinct Telegram chat/channel ID
- Route different event types (new releases, errors, dbt-package updates) to different channels
- Integrate into the existing `run_pipeline` flow, parallel to the email function
- Store bot token and all channel IDs in GCP Secret Manager

**Non-Goals:**
- Interactive Telegram bot (no command handling or two-way communication)
- Per-user DM notifications
- Replacing or removing the existing email notification path
- A Telegram admin UI or dynamic channel management at runtime

## Decisions

### 1. Module-level functions, not a class

A standalone `src/telegram_notifier.py` module with a `send_notification(bot_token, channel_id, message)` function and a `notify_releases(...)` convenience wrapper — matching the style of `_call_email_function` in `pipeline.py`.

**Why over a class:** The pipeline calls notification once per run with no shared state. A class adds no value over a plain function in this context.

### 2. Channel config via GCP Secret Manager

Channel IDs are stored as individual secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_RELEASES`, `TELEGRAM_CHANNEL_ERRORS`, `TELEGRAM_CHANNEL_DBT_PACKAGES`.

**Why over a config file or env vars:** Consistent with the existing pattern (`EMAIL_FUNCTION_URL`, `GITHUB_TOKEN`, etc.). Secrets are not committed to the repo and are rotated without redeployment.

**Alternative considered:** A single JSON secret holding all channel IDs — simpler to extend but harder to grant least-privilege IAM access per secret.

### 3. Fire-and-forget with logged errors

Telegram API calls use `requests.post` with a timeout. Failures are logged as warnings and do not raise — mirroring `_call_email_function`'s error handling.

**Why:** Notification failure must never interrupt or fail the pipeline run. The release data is already persisted to R2 before notification.

### 4. Message format: plain Markdown via Telegram MarkdownV2

Messages use Telegram's MarkdownV2 mode: bold repo name, version tag, short summary, and a URL. Kept to a single short paragraph per release to avoid flooding channels.

**Why over HTML mode:** MarkdownV2 is more readable to author and aligns with how the rest of the codebase formats strings. HTML would require escaping every `<` and `>`.

### 5. Integration point: end of `run_pipeline`, after digest build

Telegram notifications are dispatched in `run_pipeline` immediately after `_call_email_function`, using the same `new_records` list (records with `fetched_at >= run_start`).

**Why:** Ensures we only notify on genuinely new records, not backfills. Consistent with email notification timing.

## Risks / Trade-offs

- **Telegram rate limits (30 msg/s per bot, 20 msg/min per chat)** → Mitigation: batch multiple releases into a single message per channel rather than one message per release.
- **Secret Manager latency at startup** → Mitigation: secrets are fetched once in `main.py` and passed down, not re-fetched per notification.
- **MarkdownV2 escaping is strict** → Mitigation: implement a helper `_escape_md(text)` that escapes all reserved characters before injecting dynamic content.
- **Channel IDs not configured** → if a secret is missing, log a warning and skip that channel (non-fatal), matching the `email_function_url` optional pattern.

## Migration Plan

1. Add `src/telegram_notifier.py`
2. Update `src/pipeline.py`: add `telegram_config` param to `run_pipeline`, call `notify_telegram` after email dispatch
3. Update `src/main.py`: fetch Telegram secrets from Secret Manager, pass to `run_pipeline`
4. Add `TELEGRAM_BOT_TOKEN` and channel ID secrets in GCP Secret Manager for the production project
5. Deploy via existing `cloudbuild.yaml` — no schema or infrastructure changes required

**Rollback:** Remove the three secret lookups in `main.py` and the `notify_telegram` call in `pipeline.py`. All other code is additive.

## Open Questions

- Which channel types should be supported at launch — releases only, or also errors and dbt-package updates?
- Should dbt-package releases be routed to the same channel as regular releases, or a dedicated `TELEGRAM_CHANNEL_DBT_PACKAGES`?
- Maximum message length per Telegram notification (API limit is 4096 chars) — do we truncate the summary or send multiple messages?
