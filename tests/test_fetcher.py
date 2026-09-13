from unittest.mock import MagicMock, patch

import pytest

from src.fetcher import (
    GitHubFetchError,
    backfill_releases,
    fetch_gcp_docs_releases,
    fetch_rss_releases,
    filter_trivial_changes,
    get_new_releases,
)


def _release(tag: str, published_at: str) -> dict:
    return {"tag_name": tag, "published_at": published_at, "id": hash(tag)}


def _mock_get(*pages: list[dict]) -> MagicMock:
    responses = []
    for page in pages:
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.json.return_value = page
    responses = [*(_make_resp(page) for page in pages)]
    mock = MagicMock()
    mock.side_effect = responses
    return mock


def _make_resp(data: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = data
    return resp


# --- get_new_releases ---


def test_get_new_releases_filters_by_since() -> None:
    releases = [
        _release("v3.0.0", "2026-05-10T00:00:00Z"),
        _release("v2.0.0", "2026-04-01T00:00:00Z"),
        _release("v1.0.0", "2026-01-01T00:00:00Z"),
    ]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = get_new_releases("owner", "repo", since="2026-03-01T00:00:00Z")
    tags = [r["tag_name"] for r in result]
    assert "v3.0.0" in tags
    assert "v2.0.0" in tags
    assert "v1.0.0" not in tags


def test_get_new_releases_returns_ascending_order() -> None:
    releases = [
        _release("v3.0.0", "2026-05-10T00:00:00Z"),
        _release("v2.0.0", "2026-04-01T00:00:00Z"),
    ]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = get_new_releases("owner", "repo", since="2026-01-01T00:00:00Z")
    assert result[0]["tag_name"] == "v2.0.0"
    assert result[1]["tag_name"] == "v3.0.0"


def test_get_new_releases_raises_on_error() -> None:
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 404
    resp.text = "Not Found"
    with patch("src.fetcher.requests.get", return_value=resp):
        with pytest.raises(GitHubFetchError) as exc:
            get_new_releases("owner", "repo", since="2026-01-01T00:00:00Z")
    assert exc.value.status == 404


# --- backfill_releases ---


def test_backfill_keeps_last_two_majors() -> None:
    releases = [
        _release("v12.1.0", "2026-05-01T00:00:00Z"),
        _release("v12.0.0", "2026-04-01T00:00:00Z"),
        _release("v11.5.0", "2026-03-01T00:00:00Z"),
        _release("v11.0.0", "2026-02-01T00:00:00Z"),
        _release("v10.9.0", "2026-01-01T00:00:00Z"),
    ]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = backfill_releases("owner", "repo")
    tags = {r["tag_name"] for r in result}
    assert "v12.1.0" in tags
    assert "v12.0.0" in tags
    assert "v11.5.0" in tags
    assert "v11.0.0" in tags
    assert "v10.9.0" not in tags


def test_backfill_non_semver_fallback() -> None:
    releases = [_release(f"nightly-{i}", f"2026-0{(i % 9) + 1}-01T00:00:00Z") for i in range(1, 25)]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = backfill_releases("owner", "repo")
    assert len(result) == 20


def test_backfill_returns_ascending_order() -> None:
    releases = [
        _release("v2.0.0", "2026-05-01T00:00:00Z"),
        _release("v1.0.0", "2026-01-01T00:00:00Z"),
    ]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = backfill_releases("owner", "repo")
    assert result[0]["tag_name"] == "v1.0.0"
    assert result[1]["tag_name"] == "v2.0.0"


def test_backfill_min_version_filters_below() -> None:
    releases = [
        _release("v1.5.0", "2026-05-01T00:00:00Z"),
        _release("v1.0.0", "2026-03-01T00:00:00Z"),
        _release("v0.9.0", "2026-01-01T00:00:00Z"),
    ]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = backfill_releases("owner", "repo", min_version="1.0.0")
    tags = {r["tag_name"] for r in result}
    assert "v1.5.0" in tags
    assert "v1.0.0" in tags
    assert "v0.9.0" not in tags


def test_backfill_min_version_exact_match_included() -> None:
    releases = [_release("v1.0.0", "2026-01-01T00:00:00Z")]
    with patch("src.fetcher.requests.get", side_effect=[_make_resp(releases), _make_resp([])]):
        result = backfill_releases("owner", "repo", min_version="1.0.0")
    assert len(result) == 1


# ── filter_trivial_changes ───────────────────────────────────────────────────


def test_filter_removes_trivial_entries() -> None:
    changes = ["Fix typo in README", "Add new feature", "chore: bump version"]
    result = filter_trivial_changes(changes)
    assert result == ["Add new feature"]


def test_filter_keeps_all_non_trivial() -> None:
    changes = ["Improve query performance", "Support Python 3.12"]
    assert filter_trivial_changes(changes) == changes


def test_filter_skips_non_string_entries() -> None:
    changes = ["Fix typo", 42, None, "Real change"]  # type: ignore[list-item]
    result = filter_trivial_changes(changes)
    assert result == ["Real change"]


# ── fetch_gcp_docs_releases ──────────────────────────────────────────────────

_SAMPLE_GCP_DOCS = """\
# BigQuery release notes

## May 20, 2026

Feature Python UDFs are now Generally Available (GA).

## May 14, 2026

Issue Support for AI.KEY_DRIVERS has been temporarily disabled.

## December 15, 2025

Feature Some old feature.
"""


def _make_text_resp(text: str) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.text = text
    return resp


def test_gcp_docs_parses_date_sections() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(_SAMPLE_GCP_DOCS)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
        )
    tags = [r["tag_name"] for r in result]
    assert "2026-05-20" in tags
    assert "2026-05-14" in tags


def test_gcp_docs_min_date_excludes_old_entries() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(_SAMPLE_GCP_DOCS)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
            min_date="2026-01-01",
        )
    tags = [r["tag_name"] for r in result]
    assert "2025-12-15" not in tags
    assert "2026-05-20" in tags


def test_gcp_docs_since_skips_on_or_before_cursor() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(_SAMPLE_GCP_DOCS)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
            since="2026-05-14T00:00:00+00:00",
        )
    tags = [r["tag_name"] for r in result]
    assert "2026-05-14" not in tags
    assert "2026-05-20" in tags


def test_gcp_docs_returns_ascending_order() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(_SAMPLE_GCP_DOCS)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
            min_date="2026-01-01",
        )
    dates = [r["published_at"] for r in result]
    assert dates == sorted(dates)


def test_gcp_docs_record_fields() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(_SAMPLE_GCP_DOCS)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
            min_date="2026-01-01",
        )
    r = next(r for r in result if r["tag_name"] == "2026-05-20")
    assert r["name"] == "BigQuery — May 20, 2026"
    assert "Python UDFs" in str(r["body"])
    assert "May_20_2026" in str(r["html_url"])
    assert r["prerelease"] is False


def test_gcp_docs_raises_on_http_error() -> None:
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 404
    with patch("src.fetcher.requests.get", return_value=resp):
        with pytest.raises(RuntimeError, match="404"):
            fetch_gcp_docs_releases(
                url="https://example.com/release-notes.md.txt",
                display_name="BigQuery",
                docs_base_url="https://example.com/release-notes",
            )


def test_gcp_docs_anchor_format_titlecase_underscore() -> None:
    docs = "## October 01, 2026\n\nFeature something new."
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(docs)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
        )
    assert len(result) == 1
    assert "October_01_2026" in str(result[0]["html_url"])
    assert "october" not in str(result[0]["html_url"])


def test_gcp_docs_skips_sections_without_body() -> None:
    docs = "## May 20, 2026\n\n## May 14, 2026\n\nFeature something."
    with patch("src.fetcher.requests.get", return_value=_make_text_resp(docs)):
        result = fetch_gcp_docs_releases(
            url="https://example.com/release-notes.md.txt",
            display_name="BigQuery",
            docs_base_url="https://example.com/release-notes",
        )
    tags = [r["tag_name"] for r in result]
    assert "2026-05-20" not in tags
    assert "2026-05-14" in tags


# ── fetch_rss_releases ───────────────────────────────────────────────────────

_SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Scaleway Changelog</title>
    <item>
      <title><![CDATA[Containers | Initial support for Waypoint plugin]]></title>
      <description><![CDATA[<p>We added <a href="https://example.com">support</a>.</p>]]></description>
      <link>https://www.scaleway.com/en/docs/changelog/#initial-support-for-waypoint-plugin</link>
      <guid isPermaLink="true">https://www.scaleway.com/en/docs/changelog/#initial-support-for-waypoint-plugin</guid>
      <category>serverless</category>
      <pubDate>Tue, 20 May 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title><![CDATA[Instances | Initial support for ansible modules]]></title>
      <description><![CDATA[<p>Ansible is now available.</p>]]></description>
      <link>https://www.scaleway.com/en/docs/changelog/#initial-support-for-ansible-modules</link>
      <guid isPermaLink="true">https://www.scaleway.com/en/docs/changelog/#initial-support-for-ansible-modules</guid>
      <category>compute</category>
      <pubDate>Mon, 14 May 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title><![CDATA[Old | Something from last year]]></title>
      <description><![CDATA[<p>Old feature.</p>]]></description>
      <link>https://www.scaleway.com/en/docs/changelog/#old-feature</link>
      <guid isPermaLink="true">https://www.scaleway.com/en/docs/changelog/#old-feature</guid>
      <category>compute</category>
      <pubDate>Sun, 15 Dec 2025 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def _make_rss_resp(text: str) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.content = text.encode()
    return resp


def test_rss_parses_items() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_rss_resp(_SAMPLE_RSS)):
        result = fetch_rss_releases(url="https://example.com/rss.xml", display_name="Scaleway")
    tags = [r["tag_name"] for r in result]
    assert "initial-support-for-waypoint-plugin" in tags
    assert "initial-support-for-ansible-modules" in tags


def test_rss_extracts_product_and_category() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_rss_resp(_SAMPLE_RSS)):
        result = fetch_rss_releases(url="https://example.com/rss.xml", display_name="Scaleway")
    item = next(r for r in result if r["tag_name"] == "initial-support-for-waypoint-plugin")
    assert item["product"] == "Containers"
    assert item["category"] == "serverless"
    assert item["name"] == "Containers | Initial support for Waypoint plugin"


def test_rss_strips_html_from_description() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_rss_resp(_SAMPLE_RSS)):
        result = fetch_rss_releases(url="https://example.com/rss.xml", display_name="Scaleway")
    body = next(
        str(r["body"]) for r in result if r["tag_name"] == "initial-support-for-waypoint-plugin"
    )
    assert "<p>" not in body
    assert "We added support" in body


def test_rss_min_date_excludes_old_entries() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_rss_resp(_SAMPLE_RSS)):
        result = fetch_rss_releases(
            url="https://example.com/rss.xml", display_name="Scaleway", min_date="2026-01-01"
        )
    tags = [r["tag_name"] for r in result]
    assert "old-feature" not in tags
    assert "initial-support-for-waypoint-plugin" in tags


def test_rss_since_skips_on_or_before_cursor() -> None:
    with patch("src.fetcher.requests.get", return_value=_make_rss_resp(_SAMPLE_RSS)):
        result = fetch_rss_releases(
            url="https://example.com/rss.xml",
            display_name="Scaleway",
            since="2026-05-14T00:00:00+00:00",
        )
    tags = [r["tag_name"] for r in result]
    assert "initial-support-for-ansible-modules" not in tags
    assert "initial-support-for-waypoint-plugin" in tags


def test_rss_raises_on_api_error() -> None:
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 404
    with patch("src.fetcher.requests.get", return_value=resp):
        with pytest.raises(RuntimeError, match="404"):
            fetch_rss_releases(url="https://example.com/rss.xml", display_name="Scaleway")
