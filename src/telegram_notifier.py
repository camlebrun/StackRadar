from __future__ import annotations

import logging
from typing import Any

import requests as _http

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_MESSAGE_LEN = 4096

# All characters that must be escaped in MarkdownV2
_MD_RESERVED = r"\_*[]()~`>#+-=|{}.!"


def _escape_md(text: str) -> str:
    for ch in _MD_RESERVED:
        text = text.replace(ch, f"\\{ch}")
    return text


def send_notification(bot_token: str, channel_id: str, message: str) -> None:
    url = _TELEGRAM_API.format(token=bot_token)
    try:
        resp = _http.post(
            url,
            json={"chat_id": channel_id, "text": message, "parse_mode": "MarkdownV2"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Telegram notification failed (channel %s): %s", channel_id, e)


def _format_releases(records: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for r in records:
        repo = _escape_md(str(r.get("repo", "")))
        tag = _escape_md(str(r.get("tag", "")))
        url = str(r.get("html_url", ""))
        summary_raw = (r.get("analysis") or {}).get("summary", "")
        summary = _escape_md(str(summary_raw))
        lines.append(f"*{repo}* — `{tag}`\n\n_{summary}_\n\n[→ View release]({url})")

    separator = "\n\n" + _escape_md("―" * 20) + "\n\n"
    message = separator.join(lines)
    if len(message) > _MAX_MESSAGE_LEN:
        message = message[:_MAX_MESSAGE_LEN]
    return message


def notify_releases(bot_token: str, channel_id: str, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    message = _format_releases(records)
    send_notification(bot_token, channel_id, message)


def _format_advisories(advisories: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for adv in advisories:
        repo = _escape_md(str(adv.get("repo", "")))
        ghsa = _escape_md(str(adv.get("ghsa_id", "")))
        severity = _escape_md(str((adv.get("analysis") or {}).get("severity", "unknown")))
        summary_raw = str((adv.get("analysis") or {}).get("summary", adv.get("summary", "")))
        summary = _escape_md(summary_raw)
        url = _escape_md(str(adv.get("html_url", "")))
        lines.append(f"🔒 *{repo}* \\[{severity}\\]\n{ghsa} — {summary}\n{url}")

    message = "\n\n".join(lines)
    if len(message) > _MAX_MESSAGE_LEN:
        message = message[:_MAX_MESSAGE_LEN]
    return message


def notify_advisories(bot_token: str, channel_id: str, advisories: list[dict[str, Any]]) -> None:
    if not advisories:
        return
    message = _format_advisories(advisories)
    send_notification(bot_token, channel_id, message)
