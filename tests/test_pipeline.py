from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline import run_pipeline

_GOOD_ANALYSIS = {
    "summary": "Bug fixes.",
    "key_changes": ["Fixed A"],
    "breaking_changes": [],
    "migration_notes": "",
    "cve_references": [],
    "severity": "low",
    "tags": ["bug-fix"],
}


def _make_release(
    tag: str = "v1.0.0", published_at: str = "2026-01-01T00:00:00Z"
) -> dict[str, object]:
    return {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": "Some changes.",
        "published_at": published_at,
        "html_url": f"https://github.com/owner/repo/releases/tag/{tag}",
        "author": {"login": "user"},
        "prerelease": False,
        "draft": False,
        "id": 1,
    }


@pytest.fixture
def mock_s3() -> MagicMock:
    s3 = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": []}]
    s3.get_paginator.return_value = paginator
    return s3


@pytest.fixture(autouse=True)
def _advisory_mocks() -> None:  # type: ignore[return]
    """Silence advisory and digest side effects in every test."""
    with (
        patch("src.pipeline.fetch_advisories", return_value=[]),
        patch("src.pipeline.read_all_advisories", return_value=[]),
        patch("src.pipeline.write_repo_advisories"),
        patch("src.pipeline.get_advisory_cursor", return_value=None),
        patch("src.pipeline.set_advisory_cursor"),
        patch("src.pipeline.get_digest", return_value=[]),
        patch("src.pipeline.write_digest_json", return_value="digest-abc.json"),
        patch("src.pipeline.set_run_status"),
        patch("src.pipeline.analyse_advisory", return_value=None),
    ):
        yield


def test_no_cursor_triggers_backfill(mock_s3: MagicMock) -> None:
    with (
        patch("src.pipeline.load_repos", return_value=[{"repo": "owner/repo"}]),
        patch("src.pipeline.get_cursor", return_value=None),
        patch("src.pipeline.backfill_releases", return_value=[_make_release()]) as mock_backfill,
        patch("src.pipeline.get_new_releases") as mock_incremental,
        patch("src.pipeline.release_exists", return_value=False),
        patch("src.pipeline.analyse_release", return_value=(_GOOD_ANALYSIS, None)),
        patch("src.pipeline.put_release"),
        patch("src.pipeline.set_cursor"),
    ):
        run_pipeline(mock_s3, "bucket", "key")

    mock_backfill.assert_called_once()
    mock_incremental.assert_not_called()


def test_cursor_triggers_incremental(mock_s3: MagicMock) -> None:
    cursor = "2026-01-01T00:00:00Z"
    with (
        patch("src.pipeline.load_repos", return_value=[{"repo": "owner/repo"}]),
        patch("src.pipeline.get_cursor", return_value=cursor),
        patch("src.pipeline.backfill_releases") as mock_backfill,
        patch("src.pipeline.get_new_releases", return_value=[_make_release()]) as mock_incremental,
        patch("src.pipeline.release_exists", return_value=False),
        patch("src.pipeline.analyse_release", return_value=(_GOOD_ANALYSIS, None)),
        patch("src.pipeline.put_release"),
        patch("src.pipeline.set_cursor"),
    ):
        run_pipeline(mock_s3, "bucket", "key")

    mock_incremental.assert_called_once_with("owner", "repo", cursor, None)
    mock_backfill.assert_not_called()


def test_failed_repo_continues_to_next(mock_s3: MagicMock) -> None:
    repos = [{"repo": "owner/repo1"}, {"repo": "owner/repo2"}]
    with (
        patch("src.pipeline.load_repos", return_value=repos),
        patch("src.pipeline.get_cursor", side_effect=[RuntimeError("network error"), None]),
        patch("src.pipeline.backfill_releases", return_value=[]),
        patch("src.pipeline.set_cursor"),
    ):
        result = run_pipeline(mock_s3, "bucket", "key")

    assert result["repos"]["owner/repo1"]["ok"] is False
    assert "network error" in result["repos"]["owner/repo1"]["error"]
    assert result["repos"]["owner/repo2"]["ok"] is True


def test_cursor_updated_after_storing_release(mock_s3: MagicMock) -> None:
    published = "2026-05-01T00:00:00Z"
    with (
        patch("src.pipeline.load_repos", return_value=[{"repo": "owner/repo"}]),
        patch("src.pipeline.get_cursor", return_value=None),
        patch(
            "src.pipeline.backfill_releases", return_value=[_make_release(published_at=published)]
        ),  # noqa: E501
        patch("src.pipeline.release_exists", return_value=False),
        patch("src.pipeline.analyse_release", return_value=(_GOOD_ANALYSIS, None)),
        patch("src.pipeline.put_release"),
        patch("src.pipeline.set_cursor") as mock_set_cursor,
    ):
        run_pipeline(mock_s3, "bucket", "key")

    mock_set_cursor.assert_called_once_with(mock_s3, "bucket", "owner", "repo", published)


def test_existing_release_not_reanalysed(mock_s3: MagicMock) -> None:
    with (
        patch("src.pipeline.load_repos", return_value=[{"repo": "owner/repo"}]),
        patch("src.pipeline.get_cursor", return_value=None),
        patch("src.pipeline.backfill_releases", return_value=[_make_release()]),
        patch("src.pipeline.release_exists", return_value=True),
        patch("src.pipeline.analyse_release") as mock_analyse,
        patch("src.pipeline.put_release") as mock_put,
        patch("src.pipeline.set_cursor"),
    ):
        result = run_pipeline(mock_s3, "bucket", "key")

    mock_analyse.assert_not_called()
    mock_put.assert_not_called()
    assert result["repos"]["owner/repo"]["new_releases"] == 0


def test_no_releases_cursor_unchanged(mock_s3: MagicMock) -> None:
    cursor = "2026-03-01T00:00:00Z"
    with (
        patch("src.pipeline.load_repos", return_value=[{"repo": "owner/repo"}]),
        patch("src.pipeline.get_cursor", return_value=cursor),
        patch("src.pipeline.get_new_releases", return_value=[]),
        patch("src.pipeline.set_cursor") as mock_set_cursor,
    ):
        run_pipeline(mock_s3, "bucket", "key")

    mock_set_cursor.assert_not_called()


def test_llm_delay_applies_even_after_consecutive_failures(mock_s3: MagicMock) -> None:
    """Regression: the throttle must not be gated on a prior success, or a single
    rate-limited call disables all future delays and the pipeline hammers the API."""
    releases = [_make_release(tag=f"v1.0.{i}") for i in range(3)]
    with (
        patch("src.pipeline.load_repos", return_value=[{"repo": "owner/repo"}]),
        patch("src.pipeline.get_cursor", return_value=None),
        patch("src.pipeline.backfill_releases", return_value=releases),
        patch("src.pipeline.release_exists", return_value=False),
        patch("src.pipeline.analyse_release", return_value=(None, "429 rate_limited")),
        patch("src.pipeline.put_release"),
        patch("src.pipeline.set_cursor"),
        patch("src.pipeline.time.sleep") as mock_sleep,
    ):
        run_pipeline(mock_s3, "bucket", "key", llm_delay_s=1.2)

    assert mock_sleep.call_count == len(releases) - 1


def test_rss_source_skips_llm_and_tags_by_product_and_category(mock_s3: MagicMock) -> None:
    """RSS items (e.g. Scaleway) are too short to need LLM analysis — they're stored
    directly, tagged by the feed's product/category pair instead of an LLM call."""
    rss_release = {
        "tag_name": "some-feature",
        "name": "Functions | Some feature shipped",
        "body": "Short changelog blurb.",
        "published_at": "2026-05-01T00:00:00+00:00",
        "html_url": "https://example.com/changelog#some-feature",
        "prerelease": False,
        "draft": False,
        "id": None,
        "author": None,
        "category": "serverless",
        "product": "Functions",
    }
    stored: dict[str, object] = {}
    with (
        patch(
            "src.pipeline.load_repos",
            return_value=[
                {
                    "repo": "scaleway/changelog",
                    "group": "scaleway",
                    "source": "rss",
                    "docs_url": "https://example.com/rss.xml",
                }
            ],
        ),
        patch("src.pipeline.get_cursor", return_value=None),
        patch("src.pipeline.fetch_rss_releases", return_value=[rss_release]),
        patch("src.pipeline.release_exists", return_value=False),
        patch("src.pipeline.analyse_release") as mock_analyse,
        patch(
            "src.pipeline.put_release",
            side_effect=lambda _s3, _b, record: stored.update(record),
        ),
        patch("src.pipeline.set_cursor"),
        patch("src.pipeline.time.sleep") as mock_sleep,
    ):
        run_pipeline(mock_s3, "bucket", "key")

    mock_analyse.assert_not_called()
    mock_sleep.assert_not_called()
    assert stored["analysis"]["tags"] == ["Functions", "serverless"]
    assert stored["analysis"]["severity"] == "none"
    assert stored["product"] == "Functions"
    assert stored["category"] == "serverless"
