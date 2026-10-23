import json
from unittest.mock import MagicMock

from src.digest import get_digest

BUCKET = "test-bucket"


def _blob(tag: str, published_at: str, with_body: bool = True) -> bytes:
    record: dict = {
        "repo": "owner/repo",
        "tag": tag,
        "published_at": published_at,
        "analysis": None,
    }  # noqa: E501
    if with_body:
        record["body"] = "raw markdown — should be stripped"
    return json.dumps(record).encode()


def _mock_s3(blobs: dict[str, bytes]) -> MagicMock:
    s3 = MagicMock()
    page = {"Contents": [{"Key": k} for k in blobs]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    s3.get_paginator.return_value = paginator

    def get_object(Bucket: str, Key: str) -> dict:
        body = MagicMock()
        body.read.return_value = blobs[Key]
        return {"Body": body}

    s3.get_object.side_effect = get_object
    return s3


def test_sorted_descending() -> None:
    blobs = {
        "releases/owner/repo/v1.json": _blob("v1", "2026-01-01T00:00:00Z"),
        "releases/owner/repo/v3.json": _blob("v3", "2026-03-01T00:00:00Z"),
        "releases/owner/repo/v2.json": _blob("v2", "2026-02-01T00:00:00Z"),
    }
    result = get_digest(_mock_s3(blobs), BUCKET, limit=10)
    assert [r["tag"] for r in result] == ["v3", "v2", "v1"]


def test_respects_limit() -> None:
    blobs = {
        f"releases/owner/repo/v{i}.json": _blob(f"v{i}", f"2026-0{i}-01T00:00:00Z")
        for i in range(1, 6)
    }
    result = get_digest(_mock_s3(blobs), BUCKET, limit=3)
    assert len(result) == 3


def test_body_stripped() -> None:
    blobs = {"releases/owner/repo/v1.json": _blob("v1", "2026-01-01T00:00:00Z", with_body=True)}
    result = get_digest(_mock_s3(blobs), BUCKET)
    assert "body" not in result[0]


def _rec(group: str, tag: str, published_at: str) -> dict:
    return {"group": group, "repo": f"o/{group}", "tag": tag, "published_at": published_at}


def test_get_digest_without_limit_returns_everything() -> None:
    blobs = {
        f"releases/owner/repo/v{i}.json": _blob(f"v{i}", f"2026-01-{i:02d}T00:00:00Z")
        for i in range(1, 11)
    }
    assert len(get_digest(_mock_s3(blobs), BUCKET, limit=None)) == 10


def test_split_by_domain_routes_by_group() -> None:
    from src.digest import split_by_domain

    records = [
        _rec("dbt-adapters", "1.0.0", "2026-01-01"),
        _rec("bigquery", "b", "2026-01-02"),
        _rec("scaleway", "s", "2026-01-03"),
        _rec("orchestration", "o", "2026-01-04"),
    ]
    domains = split_by_domain(records)
    assert [r["tag"] for r in domains["dbt"]] == ["1.0.0", "o"]
    assert [r["tag"] for r in domains["gcp"]] == ["b"]
    assert [r["tag"] for r in domains["scaleway"]] == ["s"]


def test_split_by_domain_unmapped_group_excluded() -> None:
    from src.digest import split_by_domain

    domains = split_by_domain([_rec("mystery", "x", "2026-01-01")])
    assert all(not recs for recs in domains.values())


def test_scaleway_cap_does_not_evict_dbt_adapters() -> None:
    from src.digest import split_by_domain

    scaleway = [
        _rec("scaleway", f"s{i}", f"2026-06-{i % 28 + 1:02d}T{i % 24:02d}") for i in range(338)
    ]
    adapters = [_rec("dbt-adapters", f"a{i}", f"2024-01-{i + 1:02d}") for i in range(27)]
    domains = split_by_domain(scaleway + adapters)
    assert len(domains["dbt"]) == 27
    assert len(domains["scaleway"]) == 300
