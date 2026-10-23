from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from src.store import (
    get_cursor,
    list_release_keys,
    put_release,
    release_exists,
    set_cursor,
)


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": ""}}, "op")


def _s3(head_raises: bool = False) -> MagicMock:
    s3 = MagicMock()
    if head_raises:
        s3.head_object.side_effect = _client_error("NoSuchKey")
    return s3


BUCKET = "test-bucket"
RECORD = {
    "repo": "owner/repo",
    "tag": "v1.0.0",
    "id": 1,
    "published_at": "2026-01-01T00:00:00Z",
}


def test_release_exists_true() -> None:
    s3 = _s3(head_raises=False)
    assert release_exists(s3, BUCKET, "owner", "repo", "v1.0.0") is True
    s3.head_object.assert_called_once_with(Bucket=BUCKET, Key="releases/owner/repo/v1.0.0.json")


def test_release_exists_false() -> None:
    s3 = _s3(head_raises=True)
    assert release_exists(s3, BUCKET, "owner", "repo", "v1.0.0") is False


def test_put_release_skips_existing() -> None:
    s3 = _s3(head_raises=False)
    put_release(s3, BUCKET, RECORD)
    s3.put_object.assert_not_called()


def test_put_release_writes_new() -> None:
    s3 = _s3(head_raises=True)
    put_release(s3, BUCKET, RECORD)
    s3.put_object.assert_called_once()
    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Key"] == "releases/owner/repo/v1.0.0.json"
    assert call_kwargs["ContentType"] == "application/json"


def test_get_cursor_none_when_missing() -> None:
    s3 = MagicMock()
    s3.get_object.side_effect = _client_error("NoSuchKey")
    assert get_cursor(s3, BUCKET, "owner", "repo") is None


def test_set_cursor_writes_correct_key() -> None:
    s3 = MagicMock()
    set_cursor(s3, BUCKET, "owner", "repo", "2026-05-01T00:00:00Z")
    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Key"] == "meta/cursor/owner/repo.json"
    assert b"2026-05-01T00:00:00Z" in call_kwargs["Body"]


def test_list_release_keys_uses_prefix() -> None:
    page = {"Contents": [{"Key": "releases/owner/repo/v1.0.0.json"}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    s3 = MagicMock()
    s3.get_paginator.return_value = paginator
    keys = list_release_keys(s3, BUCKET)
    paginator.paginate.assert_called_once_with(Bucket=BUCKET, Prefix="releases/")
    assert keys == ["releases/owner/repo/v1.0.0.json"]


def test_write_domain_digests_keys_and_security_payload() -> None:
    import json

    from src.store import write_domain_digests

    s3 = MagicMock()
    keys = write_domain_digests(
        s3, "b", {"dbt": [{"tag": "v1", "body": "x"}], "gcp": []}, [{"id": "CVE-1"}]
    )
    assert set(keys) == {"dbt", "gcp", "security"}
    assert keys["dbt"].startswith("digest-dbt-")
    bodies = {c.kwargs["Key"]: json.loads(c.kwargs["Body"]) for c in s3.put_object.call_args_list}
    assert bodies[keys["dbt"]]["releases"] == [{"tag": "v1"}]
    assert bodies[keys["security"]] == {"releases": [], "advisories": [{"id": "CVE-1"}]}


def test_manifest_lists_domain_digests_and_keeps_combined_key() -> None:
    import json

    from src.store import write_digest_json

    s3 = MagicMock()
    key = write_digest_json(s3, "b", [], [], {"dbt": "digest-dbt-1.json"})
    manifest = next(
        json.loads(c.kwargs["Body"])
        for c in s3.put_object.call_args_list
        if c.kwargs["Key"] == "manifest.json"
    )
    assert manifest["digest"] == key
    assert manifest["digests"] == {"dbt": "digest-dbt-1.json"}


def test_manifest_without_domains_has_no_digests_key() -> None:
    import json

    from src.store import write_digest_json

    s3 = MagicMock()
    write_digest_json(s3, "b", [])
    manifest = json.loads(s3.put_object.call_args_list[-1].kwargs["Body"])
    assert "digests" not in manifest
