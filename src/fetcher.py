from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import requests

from src.analyser import filter_trivial_changes
from src.config import (
    BACKFILL_NON_SEMVER,
    GITHUB_API_BASE,
    GITHUB_RETRY_MAX,
    GITHUB_TIMEOUT_S,
    MAX_RELEASES_PER_RUN,
)
from src.semver import parse_semver

logger = logging.getLogger(__name__)

_PROD_BREAKING_BUG_PATTERNS = [
    "fix",
    "bug",
    "crash",
    "error",
    "broken",
    "regression",
    "exception",
    "fails",
    "failure",
    "incorrect",
    "wrong result",
    "typeerror",
    "attributeerror",
    "keyerror",
    "importerror",
    "null",
    "none type",
    "data loss",
    "silent",
    "incorrect result",
]


class GitHubFetchError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API error {status}: {message}")
        self.status = status


def fetch_readme(owner: str, repo: str, token: str | None = None) -> str:
    """Fetch README content from GitHub API, return plain text (truncated to 3000 chars)."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    try:
        resp = requests.get(
            url,
            headers=_github_headers(token, accept="application/vnd.github.raw+json"),
            timeout=GITHUB_TIMEOUT_S,
        )
        if resp.ok:
            return resp.text[:3000]
    except Exception as e:
        logger.warning("Could not fetch README for %s/%s: %s", owner, repo, e)
    return ""


def heuristic_dbt_analysis(
    release: dict[str, object],
    readme: str,
) -> dict[str, object]:
    """Rule-based dbt package analysis — no LLM required, used for testing."""
    from src.semver import parse_semver

    tag = str(release.get("tag_name", ""))
    body = str(release.get("body", "")).lower()
    name = str(release.get("name", tag))
    sv = parse_semver(tag)

    # Detect prod-breaking bug
    is_prod_breaking_bug = any(p in body for p in _PROD_BREAKING_BUG_PATTERNS) and sv.patch > 0

    # Determine severity
    if "data loss" in body or "corruption" in body or "silent" in body:
        severity = "critical"
    elif "crash" in body or "exception" in body or "typeerror" in body or "keyerror" in body:
        severity = "high"
    elif is_prod_breaking_bug:
        severity = "medium"
    elif sv.minor > 0 and sv.patch == 0:
        severity = "low"
    else:
        severity = "none"

    # Extract purpose from first non-empty README paragraph (strip HTML tags)
    purpose = ""
    for para in readme.split("\n\n"):
        clean = para.strip().lstrip("#").strip()
        clean = re.sub(r"<[^>]+>", "", clean).strip()  # strip HTML tags
        clean = re.sub(r"\s+", " ", clean)  # collapse whitespace
        if len(clean) > 40 and not clean.startswith("!"):
            purpose = clean[:300]
            break

    # Parse key changes from release body bullet points (skip markdown headers)
    raw_changes = []
    for line in str(release.get("body", "")).splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        stripped = stripped.lstrip("-*•").strip()
        if stripped and len(stripped) > 10:
            raw_changes.append(stripped)
    key_changes = filter_trivial_changes(raw_changes[:10])[:6]

    tags: list[str] = []
    if is_prod_breaking_bug:
        tags.append("bug-fix")
    if sv.patch == 0 and sv.minor == 0:
        tags.append("breaking")
    if not key_changes:
        tags.append("docs-only")
    if not tags:
        tags.append("feature" if sv.patch == 0 else "bug-fix")

    return {
        "purpose": purpose or f"{release.get('repo', '')} dbt package.",
        "summary": f"{name} — {'patch fix' if sv.patch > 0 else 'minor/major release'}.",
        "key_changes": key_changes,
        "is_prod_breaking_bug": is_prod_breaking_bug,
        "severity": severity,
        "tags": tags,
    }


def _github_headers(
    token: str | None,
    *,
    accept: str = "application/vnd.github+json",
) -> dict[str, str]:
    h: dict[str, str] = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get_page(url: str, token: str | None, params: dict[str, int | str]) -> list[dict[str, object]]:
    for attempt in range(GITHUB_RETRY_MAX):
        resp = requests.get(
            url, headers=_github_headers(token), params=params, timeout=GITHUB_TIMEOUT_S
        )
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = 2**attempt
            logger.warning(
                "GitHub %s, retrying in %ss (attempt %s)", resp.status_code, wait, attempt + 1
            )  # noqa: E501
            time.sleep(wait)
            continue
        if not resp.ok:
            raise GitHubFetchError(resp.status_code, resp.text[:200])
        return resp.json()  # type: ignore[no-any-return]
    raise GitHubFetchError(429, "Max retries exceeded")


def _all_pages(owner: str, repo: str, token: str | None) -> list[dict[str, object]]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    releases: list[dict[str, object]] = []
    page = 1
    while True:
        page_data = _get_page(url, token, {"per_page": 100, "page": page})
        if not page_data:
            break
        releases.extend(page_data)
        page += 1
    return releases


def get_new_releases(
    owner: str, repo: str, since: str, token: str | None = None
) -> list[dict[str, object]]:
    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    result: list[dict[str, object]] = []
    page = 1
    done = False
    while not done:
        page_data = _get_page(url, token, {"per_page": 100, "page": page})
        if not page_data:
            break
        for release in page_data:
            pub = datetime.fromisoformat(str(release["published_at"]).replace("Z", "+00:00"))
            if pub <= since_dt:
                done = True
                break
            result.append(release)
            if len(result) >= MAX_RELEASES_PER_RUN:
                done = True
                break
        page += 1

    result.sort(key=lambda r: str(r["published_at"]))
    return result


def backfill_releases(
    owner: str,
    repo: str,
    token: str | None = None,
    min_version: str | None = None,
    stable_only: bool = False,
    minor_only: bool = False,
) -> list[dict[str, object]]:
    all_releases = _all_pages(owner, repo, token)
    if not all_releases:
        return []

    semver_releases = [(r, parse_semver(str(r["tag_name"]))) for r in all_releases]
    valid = [(r, sv) for r, sv in semver_releases if sv.valid]

    if not valid:
        sorted_all = sorted(all_releases, key=lambda r: str(r["published_at"]))
        return sorted_all[-BACKFILL_NON_SEMVER:]

    if min_version:
        min_sv = parse_semver(min_version)
        if min_sv.valid:
            valid = [
                (r, sv)
                for r, sv in valid
                if (sv.major, sv.minor, sv.patch) >= (min_sv.major, min_sv.minor, min_sv.patch)
            ]
    else:
        max_major = max(sv.major for _, sv in valid)
        valid = [(r, sv) for r, sv in valid if sv.major >= max_major - 1]

    if stable_only:
        valid = [(r, sv) for r, sv in valid if not r.get("prerelease")]
    if minor_only:
        valid = [(r, sv) for r, sv in valid if sv.patch == 0]
    valid.sort(key=lambda x: str(x[0]["published_at"]))
    return [r for r, _ in valid]


# ---------------------------------------------------------------------------
# Google Cloud Docs release notes fetcher (date-based, reusable across services)
# ---------------------------------------------------------------------------

_GCP_DOCS_TIMEOUT_S = 20
_GCP_DATE_RE = re.compile(r"^(\w+ \d{1,2}, \d{4})$")


def fetch_gcp_docs_releases(
    url: str,
    display_name: str,
    docs_base_url: str,
    since: str | None = None,
    min_date: str | None = None,
) -> list[dict[str, object]]:
    """Fetch Google Cloud Docs release notes from a .md.txt URL.

    Each ## Month DD, YYYY section becomes one release-like record.
    url: the .md.txt source URL.
    display_name: human label used in record name (e.g. 'BigQuery', 'Lakehouse').
    docs_base_url: base URL for html_url anchors (e.g. 'https://cloud.google.com/bigquery/docs/release-notes').
    since: ISO timestamp cursor — entries on or before this date are skipped.
    min_date: ISO date lower bound used when since is None (e.g. '2026-01-01').
    """
    resp = requests.get(url, timeout=_GCP_DOCS_TIMEOUT_S)
    if not resp.ok:
        raise RuntimeError(f"{display_name} release notes fetch failed: {resp.status_code}")

    raw = resp.text
    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    if min_date and not since_dt:
        min_dt = datetime.fromisoformat(min_date + "T00:00:00+00:00")
    else:
        min_dt = None

    sections = re.split(r"^## ", raw, flags=re.MULTILINE)
    releases: list[dict[str, object]] = []

    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue
        header = lines[0].strip()
        m = _GCP_DATE_RE.match(header)
        if not m:
            continue

        try:
            dt = datetime.strptime(m.group(1), "%B %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        if since_dt and dt <= since_dt:
            continue
        if min_dt and dt < min_dt:
            continue

        body = "\n".join(lines[1:]).strip()
        if not body:
            continue

        tag = dt.strftime("%Y-%m-%d")
        anchor = dt.strftime("%B_%d_%Y")

        releases.append(
            {
                "tag_name": tag,
                "name": f"{display_name} — {header}",
                "body": body,
                "published_at": dt.isoformat(),
                "html_url": f"{docs_base_url}#{anchor}",
                "prerelease": False,
                "draft": False,
                "id": None,
                "author": None,
            }
        )

    return sorted(releases, key=lambda r: str(r["published_at"]))


# ---------------------------------------------------------------------------
# RSS feed fetcher (date-based, one item per feature — e.g. Scaleway changelog)
# ---------------------------------------------------------------------------

_RSS_TIMEOUT_S = 20
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", _HTML_TAG_RE.sub(" ", text)).strip()


def fetch_rss_releases(
    url: str,
    display_name: str,
    since: str | None = None,
    min_date: str | None = None,
) -> list[dict[str, object]]:
    """Fetch a standard RSS 2.0 feed. Each <item> becomes one release-like record.

    url: the feed's .xml URL.
    display_name: human label used in record name if the item has no title.
    since: ISO timestamp cursor — items on or before this date are skipped.
    min_date: ISO date lower bound used when since is None (e.g. '2026-01-01').
    """
    resp = requests.get(url, timeout=_RSS_TIMEOUT_S)
    if not resp.ok:
        raise RuntimeError(f"{display_name} RSS fetch failed: {resp.status_code}")

    root = ElementTree.fromstring(resp.content)
    since_dt = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    if min_date and not since_dt:
        min_dt = datetime.fromisoformat(min_date + "T00:00:00+00:00")
    else:
        min_dt = None

    releases: list[dict[str, object]] = []
    for item in root.findall(".//item"):
        pub_date_raw = item.findtext("pubDate")
        if not pub_date_raw:
            continue
        try:
            dt = parsedate_to_datetime(pub_date_raw)
        except (TypeError, ValueError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        if since_dt and dt <= since_dt:
            continue
        if min_dt and dt < min_dt:
            continue

        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        title = (item.findtext("title") or display_name).strip()
        description = _strip_html(item.findtext("description") or "")
        category = (item.findtext("category") or "").strip()

        product, _, _headline = title.partition(" | ")
        product = product.strip() if _headline else ""

        tag = link.rsplit("#", 1)[-1] or guid.rsplit("/", 1)[-1] or dt.strftime("%Y-%m-%dT%H%M%S")

        releases.append(
            {
                "tag_name": tag,
                "name": title,
                "body": description,
                "published_at": dt.isoformat(),
                "html_url": link or guid,
                "prerelease": False,
                "draft": False,
                "id": None,
                "author": None,
                "category": category,
                "product": product,
            }
        )

    return sorted(releases, key=lambda r: str(r["published_at"]))
