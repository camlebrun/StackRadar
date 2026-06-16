## 1. Core Notifier Module

- [x] 1.1 Create `src/telegram_notifier.py` with `_escape_md(text)` helper that escapes all MarkdownV2 reserved characters
- [x] 1.2 Implement `send_notification(bot_token, channel_id, message)` — POST to Telegram Bot API with timeout, log warning on failure (non-fatal)
- [x] 1.3 Implement `_format_releases(records)` — formats a list of release records into a single MarkdownV2 message (bold repo, tag, truncated summary ≤ 120 chars, URL), truncating full message at 4096 chars
- [x] 1.4 Implement `notify_releases(bot_token, channel_id, records)` — no-op if records empty, else call `_format_releases` then `send_notification`
- [x] 1.5 Write unit tests in `tests/test_telegram_notifier.py` covering: escaping, formatting, empty-records no-op, and API failure non-fatal behavior

## 2. Channel Config (Secret Manager — Cost Optimised)

- [x] 2.1 In `src/main.py`, fetch `TELEGRAM_BOT_TOKEN` once at startup using `get_secret`; on failure log warning and set `telegram_config = None`
- [x] 2.2 If bot token resolves, fetch each channel secret (`TELEGRAM_CHANNEL_RELEASES`, `TELEGRAM_CHANNEL_ERRORS`, `TELEGRAM_CHANNEL_DBT_PACKAGES`, `TELEGRAM_CHANNEL_SECURITY`) in a single loop — skip missing secrets silently (try/except per key, no retry)
- [x] 2.3 Build `telegram_config = {"bot_token": token, "channels": {...}}` dict from resolved secrets; pass to `run_pipeline`

> **Cost note:** All Secret Manager fetches happen once per pipeline run at startup (not per-repo or per-notification). This keeps Secret Manager API calls to ≤ 4 per run regardless of the number of repos or releases processed.

## 3. Pipeline Integration

- [x] 3.1 Add `telegram_config: dict | None = None` parameter to `run_pipeline` in `src/pipeline.py`
- [x] 3.2 After the email function call in `run_pipeline`, call `notify_releases` for the `releases` channel if configured, passing `new_records`
- [x] 3.3 Add error-channel notification: if any repo in `repo_status` has `ok: False` and `TELEGRAM_CHANNEL_ERRORS` is configured, send a failure summary to the errors channel
- [x] 3.4 Route dbt-package records separately: filter `new_records` by `is_dbt_package`-flagged repos and send to `TELEGRAM_CHANNEL_DBT_PACKAGES` if configured (fall back to releases channel if not)

## 4. GCP Secret Manager Setup

- [x] 4.1 Create `TELEGRAM_BOT_TOKEN` secret in GCP Secret Manager for project `git-release-496817`
- [x] 4.2 Create `TELEGRAM_CHANNEL_DBT_CORE` secret (dbt-core, dbt-fusion, adaptateurs)
- [x] 4.3 Create `TELEGRAM_CHANNEL_DBT_PACKAGES` secret (releases dbt packages)
- [x] 4.4 Create `TELEGRAM_CHANNEL_ORCHESTRATION` secret (Dagster, Kestra, Airflow)
- [x] 4.5 Create `TELEGRAM_CHANNEL_GCP` secret (BigQuery, Lakehouse)
- [x] 4.6 Create `TELEGRAM_CHANNEL_ERRORS` secret (erreurs pipeline)
- [x] 4.7 Create `TELEGRAM_CHANNEL_SECURITY` secret (security advisories)
- [x] 4.8 Grant the Cloud Run service account `roles/secretmanager.secretAccessor` on all 7 secrets

## 5. Validation

- [ ] 5.1 Run `pytest tests/test_telegram_notifier.py` — all tests pass
- [ ] 5.2 Run existing test suite (`pytest`) to confirm no regressions
- [ ] 5.3 Do a local dry-run with `TELEGRAM_BOT_TOKEN` set and a test channel ID to verify message format and delivery
