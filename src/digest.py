from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.config import (
    DIGEST_DEFAULT_LIMIT,
    DIGEST_DOMAIN_LIMITS,
    DIGEST_DOMAINS,
    DIGEST_MAX_LIMIT,
)
from src.store import list_release_keys

logger = logging.getLogger(__name__)

_BATCH = 20


def _build_repo_overrides() -> dict[str, dict[str, Any]]:
    from src.pipeline import load_repos

    overrides: dict[str, dict[str, Any]] = {}
    for item in load_repos():
        fields: dict[str, Any] = {}
        if item.get("deprecated"):
            fields["deprecated"] = True
            fields["deprecated_notice"] = item.get("deprecated_notice")
        if item.get("notice"):
            fields["notice"] = item["notice"]
        if fields:
            overrides[item["repo"]] = fields
    return overrides


def _fetch_one(s3: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        record = json.loads(resp["Body"].read())
        record.pop("body", None)
        return record  # type: ignore[no-any-return]
    except Exception as e:
        logger.warning("Failed to fetch digest record %s: %s", key, e)
        return None


def get_digest(
    s3: Any, bucket: str, limit: int | None = DIGEST_DEFAULT_LIMIT
) -> list[dict[str, Any]]:
    """Newest-first records; `limit=None` returns every stored release."""
    if limit is not None:
        limit = min(limit, DIGEST_MAX_LIMIT)
    keys = list_release_keys(s3, bucket)
    deprecated_map = _build_repo_overrides()

    records: list[dict[str, Any]] = []
    for i in range(0, len(keys), _BATCH):
        batch = keys[i : i + _BATCH]
        with ThreadPoolExecutor(max_workers=_BATCH) as executor:
            futures = {executor.submit(_fetch_one, s3, bucket, k): k for k in batch}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    # Inject deprecated status from repos.json (overrides stale R2 records)
                    repo = result.get("repo", "")
                    if repo in deprecated_map:
                        result.update(deprecated_map[repo])
                    records.append(result)

    records.sort(key=lambda r: str(r.get("published_at", "")), reverse=True)
    return records[:limit]


def split_by_domain(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Route newest-first records to their domain digest by `group`, applying per-domain caps."""
    domain_of = {group: domain for domain, groups in DIGEST_DOMAINS.items() for group in groups}
    domains: dict[str, list[dict[str, Any]]] = {domain: [] for domain in DIGEST_DOMAINS}
    unmapped: set[str] = set()
    for record in records:
        group = str(record.get("group") or "")
        if group in domain_of:
            domains[domain_of[group]].append(record)
        else:
            unmapped.add(group)
    if unmapped:
        logger.warning("Records with unmapped group kept out of domain digests: %s", unmapped)
    for domain, limit in DIGEST_DOMAIN_LIMITS.items():
        domains[domain] = domains[domain][:limit]
    return domains
