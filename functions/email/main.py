"""Cloud Function — email digest sender (internal, requires OIDC auth from Cloud Run)."""

from __future__ import annotations

import base64
import html
import json
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import functions_framework
from flask import Request, Response
from google.cloud import secretmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GCP_PROJECT = "git-release-496817"

# Same badge pairs as the site (public/style.css --sev-*), all >= 4.5:1.
_SEV_BG = {
    "critical": "#f6dcd3",
    "high": "#f8e3cd",
    "medium": "#f7ecc6",
    "low": "#e1ebe3",
    "none": "#ece6dc",
}
_SEV_FG = {
    "critical": "#8f2a12",
    "high": "#8a4300",
    "medium": "#6b5200",
    "low": "#2f5d3d",
    "none": "#5d6677",
}

_TEMPLATES = Path(__file__).parent / "templates"

_ICON_URL = "https://pub-d7a866e02d744f3fb57bc3859858a5df.r2.dev/icon.png"

# Module-level secret cache — loaded once per cold start
_secrets: dict[str, str] = {}
_icon_data_url: str | None = None


def _get_secret(name: str) -> str:
    if name not in _secrets:
        client = secretmanager.SecretManagerServiceClient()
        path = f"projects/{GCP_PROJECT}/secrets/{name}/versions/latest"
        _secrets[name] = client.access_secret_version(name=path).payload.data.decode()
    return _secrets[name]


def _safe_text(s: str) -> str:
    """Normalize common non-ASCII lookalikes from LLM output to plain UTF-8."""
    return (
        s.replace("\xa0", " ")  # non-breaking space → regular space
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )


# Same display names as the site (public/app.js REPO_DISPLAY).
_REPO_DISPLAY = {
    "dagster-io/dagster": "Dagster",
    "kestra-io/kestra": "Kestra",
    "apache/airflow": "Airflow",
}


def _h(value: Any) -> str:
    """HTML-escape LLM / GitHub text before it goes into the template."""
    return html.escape(_safe_text(str(value)))


def _format_date(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return f"{d:%b} {d.day}, {d.year}"


def _render_card(r: dict[str, Any]) -> str:
    """Same card as the site: repo, severity, serif title, date, summary, changes, tags."""
    a = r.get("analysis") or {}
    sev = a.get("severity", "none")
    repo = r.get("repo", "")
    changes = a.get("key_changes", [])[:3]
    changes_block = ""
    if changes:
        items = "".join(
            f'<li style="margin:6px 0;color:#5d6677;-webkit-text-fill-color:#5d6677;font-size:13px;line-height:1.5;">'
            f'<span style="color:#8d4f26;-webkit-text-fill-color:#8d4f26;font-weight:700;margin-right:8px;">&rsaquo;</span>'
            f"{_h(c)}</li>"
            for c in changes
        )
        changes_block = f'<ul style="margin:0;padding:0;list-style:none;">{items}</ul>'

    tags = [t for t in a.get("tags", []) if t != "pre-release"][:3]
    tags_block = "".join(
        '<span style="display:inline-block;background:#f4ebe3;color:#8d4f26;border:1px solid #e8dbcf;'
        f'border-radius:6px;padding:3px 8px;font-size:11px;font-weight:500;margin-right:6px;">{_h(t)}</span>'
        for t in tags
    )

    tpl = (_TEMPLATES / "email_card.html").read_text()
    return (
        tpl.replace("{{sev_bg}}", _SEV_BG.get(sev, _SEV_BG["none"]))
        .replace("{{sev_fg}}", _SEV_FG.get(sev, _SEV_FG["none"]))
        .replace("{{severity}}", _h(sev))
        .replace("{{repo_label}}", _h(_REPO_DISPLAY.get(repo, repo.split("/")[-1])))
        .replace("{{title}}", _h(r.get("name") or r.get("tag", "")))
        .replace("{{date}}", _format_date(str(r.get("published_at", ""))))
        .replace("{{summary}}", _h(a.get("summary", "No summary available.")))
        .replace("{{changes_block}}", changes_block)
        .replace("{{tags_block}}", tags_block)
        .replace("{{url}}", html.escape(str(r.get("html_url", "#"))))
    )


def _build_html(releases: list[dict[str, Any]]) -> str:
    count = len(releases)
    cards = "".join(_render_card(r) for r in releases)
    tpl = (_TEMPLATES / "email_digest.html").read_text()
    return (
        tpl.replace("{{count}}", str(count))
        .replace("{{count_plural}}", "s" if count > 1 else "")
        .replace("{{cards}}", cards)
        .replace("{{icon_data_url}}", _ICON_URL)
    )


def _fail_html(error: str, repo: str | None) -> str:
    context = (
        f"<p style='margin:0 0 8px;color:#5d6677;font-size:13px;'>"
        f"Repo: <strong>{repo}</strong></p>"
        if repo
        else ""
    )
    return (
        '<!DOCTYPE html><html><head><meta name="color-scheme" content="light only">'
        '<meta name="supported-color-schemes" content="light only"></head>'
        '<body style="margin:0;padding:0;background-color:#f5f0e8;'
        "font-family:'DM Sans',Helvetica,Arial,sans-serif;\">"
        '<div style="max-width:600px;margin:0 auto;padding:32px 16px;">'
        '<div style="margin-bottom:20px;">'
        "<span style=\"font-family:'Playfair Display',Georgia,serif;font-size:18px;"
        'font-weight:700;color:#1b2230;">StackRadar</span></div>'
        '<div style="background:#ffffff;border-radius:16px;border:1px solid #e6d8c8;'
        'border-left:3px solid #8f2a12;padding:20px 24px;">'
        '<h2 style="margin:0 0 12px;color:#8f2a12;font-size:16px;font-weight:700;">'
        "Pipeline failure</h2>"
        f"{context}"
        f'<pre style="margin:0;background:#f6dcd3;border-radius:8px;padding:12px;'
        f'font-size:12px;color:#8f2a12;overflow:auto;white-space:pre-wrap;">{error}</pre>'
        "</div>"
        '<p style="margin:20px 0 0;color:#5d6677;font-size:11px;">Sent by StackRadar</p>'
        "</div></body></html>"
    )


def _send(subject: str, html: str) -> None:
    gmail_address = _get_secret("GMAIL_ADDRESS")
    gmail_app_password = _get_secret("GMAIL_APP_PASSWORD")
    notify_email = _get_secret("NOTIFY_EMAIL")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = notify_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, notify_email, msg.as_bytes())


@functions_framework.http
def send_email(request: Request) -> Response:
    try:
        body = request.get_json(silent=True) or {}
        path = request.path.rstrip("/")

        if path == "/fail":
            error = body.get("error", "Unknown error")
            repo = body.get("repo")
            _send("[StackRadar] Pipeline failure", _fail_html(error, repo))
            logger.info("Fail email sent for repo=%s", repo)
            return Response(json.dumps({"sent": "fail"}), status=200, mimetype="application/json")

        releases = body.get("releases", [])
        if not releases:
            return Response(json.dumps({"sent": 0}), status=200, mimetype="application/json")

        count = len(releases)
        _send(
            f"[StackRadar] {count} new release{'s' if count > 1 else ''}",
            _build_html(releases),
        )
        logger.info("Digest email sent: %d releases", count)
        return Response(json.dumps({"sent": count}), status=200, mimetype="application/json")

    except Exception as e:
        logger.error("Email failed: %s", e)
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
