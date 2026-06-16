"""Cloud Run Job entry point — runs the release pipeline to completion."""

from __future__ import annotations

import logging
import sys

from src.config import GCP_PROJECT, R2_BUCKET, TelegramConfig
from src.pipeline import run_pipeline
from src.secrets import get_secret
from src.store import get_s3_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    s3 = get_s3_client(
        access_key=get_secret(GCP_PROJECT, "R2_ACCESS_KEY_ID"),
        secret_key=get_secret(GCP_PROJECT, "R2_SECRET_ACCESS_KEY"),
        account_id=get_secret(GCP_PROJECT, "R2_ACCOUNT_ID"),
    )

    llm_key = get_secret(GCP_PROJECT, "MISTRAL_API_KEY")

    try:
        github_token: str | None = get_secret(GCP_PROJECT, "GITHUB_TOKEN")
    except Exception:
        logger.warning(
            "GITHUB_TOKEN not in Secret Manager — unauthenticated GitHub requests (60 req/hr limit)"
        )
        github_token = None

    try:
        email_function_url: str | None = get_secret(GCP_PROJECT, "EMAIL_FUNCTION_URL")
    except Exception:
        logger.warning("EMAIL_FUNCTION_URL not in Secret Manager — email notifications disabled")
        email_function_url = None

    telegram_config: TelegramConfig | None = None
    try:
        tg_token = get_secret(GCP_PROJECT, "TELEGRAM_BOT_TOKEN")
        channels: dict[str, str] = {}
        for key, label in [
            ("TELEGRAM_CHANNEL_DBT_CORE", "dbt_core"),
            ("TELEGRAM_CHANNEL_DBT_PACKAGES", "dbt_packages"),
            ("TELEGRAM_CHANNEL_ORCHESTRATION", "orchestration"),
            ("TELEGRAM_CHANNEL_GCP", "gcp"),
            ("TELEGRAM_CHANNEL_ERRORS", "errors"),
            ("TELEGRAM_CHANNEL_SECURITY", "security"),
        ]:
            try:
                channels[label] = get_secret(GCP_PROJECT, key)
            except Exception:
                logger.warning("%s not in Secret Manager — skipping that channel", key)
        telegram_config = TelegramConfig(bot_token=tg_token, channels=channels)
    except Exception:
        logger.warning("TELEGRAM_BOT_TOKEN not in Secret Manager — Telegram notifications disabled")

    result = run_pipeline(
        s3,
        R2_BUCKET,
        llm_key,
        github_token,
        llm_delay_s=1.2,
        email_function_url=email_function_url,
        telegram_config=telegram_config,
    )

    failed = [repo for repo, status in result["repos"].items() if not status["ok"]]
    if failed:
        logger.error("Failed repos: %s", failed)
        sys.exit(1)

    logger.info("Job complete: %s", result["repos"])


if __name__ == "__main__":
    main()
