## ADDED Requirements

### Requirement: TelegramConfig TypedDict
A `TelegramConfig` TypedDict SHALL be defined in `src/config.py` with fields `bot_token: str` and `channels: dict[str, str]`. Both `main.py` and `pipeline.py` SHALL use this type instead of an untyped `dict`.

#### Scenario: Type-safe construction in main.py
- **WHEN** `main.py` assembles the Telegram configuration
- **THEN** it SHALL construct a `TelegramConfig` and pass it to `run_pipeline` with the declared type

#### Scenario: No defensive .get() in pipeline
- **WHEN** `pipeline.py` reads `telegram_config`
- **THEN** it SHALL access `bot_token` and `channels` as typed fields without `.get()` fallbacks

### Requirement: Telegram routing extracted from run_pipeline
`pipeline.py` SHALL define a dedicated function `_route_telegram` that handles all channel routing and notification dispatch. `run_pipeline` SHALL call `_route_telegram` instead of containing the routing logic inline.

#### Scenario: Release routing by group
- **WHEN** `_route_telegram` is called with new release records and a repo config
- **THEN** it SHALL route records to `dbt_core`, `dbt_packages`, `orchestration`, or `gcp` based on repo type and group, identical to current behavior

#### Scenario: Advisory notifications
- **WHEN** `_route_telegram` is called with new advisories
- **THEN** it SHALL dispatch to the `security` channel, identical to current behavior

#### Scenario: Pipeline error notifications
- **WHEN** `_route_telegram` is called with failed repos
- **THEN** it SHALL dispatch to the `errors` channel, identical to current behavior
