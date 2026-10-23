from __future__ import annotations

from typing import TypedDict


class TelegramConfig(TypedDict):
    bot_token: str
    channels: dict[str, str]


GCP_PROJECT = "git-release-496817"
GCP_REGION = "europe-west9"

R2_BUCKET = "git-release-releases"

MAX_RELEASES_PER_RUN = 50
BACKFILL_NON_SEMVER = 20
DIGEST_DEFAULT_LIMIT = 200
DIGEST_MAX_LIMIT = 500

# Each domain gets its own digest so a noisy source cannot evict another one.
# Records are routed by their `group`; only Scaleway (RSS, unbounded) is capped.
DIGEST_DOMAINS: dict[str, tuple[str, ...]] = {
    "dbt": ("dbt-core", "dbt-adapters", "dbt-packages", "orchestration"),
    "gcp": ("bigquery", "lakehouse"),
    "scaleway": ("scaleway",),
}
DIGEST_DOMAIN_LIMITS: dict[str, int] = {"scaleway": 300}
LLM_MAX_TOKENS = 4096
MISTRAL_MODEL = "mistral-small-latest"

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TIMEOUT_S = 10
GITHUB_RETRY_MAX = 3
