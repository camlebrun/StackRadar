from __future__ import annotations

import json
import logging

from mistralai.client import Mistral
from pydantic import BaseModel, ValidationError, model_validator

from src.config import LLM_MAX_TOKENS, MISTRAL_MODEL
from src.prompts.bigquery_release_analysis import BIGQUERY_RELEASE_ANALYSIS_PROMPT
from src.prompts.dbt_package_analysis import DBT_PACKAGE_ANALYSIS_PROMPT
from src.prompts.fusion_historical import FUSION_HISTORICAL_PROMPT
from src.prompts.fusion_release_analysis import FUSION_RELEASE_ANALYSIS_PROMPT
from src.prompts.lakehouse_release_analysis import LAKEHOUSE_RELEASE_ANALYSIS_PROMPT
from src.prompts.release_analysis import RELEASE_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

_TRIVIAL_CHANGE_PATTERNS = [
    "update readme",
    "add contributors",
    "update contributors",
    "bump version",
    "bump changelog",
    "update changelog",
    "fix typo",
    "update docs",
    "update documentation",
    "formatting",
    "linting",
    "style:",
    "chore:",
    "ci:",
    "whitespace",
]

_BLACKLISTED_SECTIONS = [
    "migrating from <1.0.0 to >=1.0.0",
    "migrating from",
]


def filter_trivial_changes(changes: list[str]) -> list[str]:
    """Remove trivial/cosmetic entries from a key_changes list."""
    result = []
    for c in changes:
        if not isinstance(c, str):
            continue
        low = c.lower()
        if any(p in low for p in _TRIVIAL_CHANGE_PATTERNS):
            continue
        if any(low.startswith(section) for section in _BLACKLISTED_SECTIONS):
            continue
        result.append(c)
    return result


class DbtPackageAnalysisResult(BaseModel):
    purpose: str
    summary: str
    key_changes: list[str] = []
    is_prod_breaking_bug: bool
    severity: str
    tags: list[str]


def _coerce_str_list(v: object) -> list[str]:
    if not isinstance(v, list):
        return []
    return [item if isinstance(item, str) else str(item) for item in v]


class BigQueryAnalysisResult(BaseModel):
    summary: str
    key_changes: list[str]
    breaking_changes: list[str] = []
    migration_notes: str = ""
    cost_and_performance_impact: str = ""
    severity: str
    tags: list[str]

    @model_validator(mode="before")
    @classmethod
    def _coerce_lists(cls, data: object) -> object:
        if isinstance(data, dict):
            for field in ("key_changes", "breaking_changes", "tags"):
                if field in data:
                    data[field] = _coerce_str_list(data[field])
        return data


class AnalysisResult(BaseModel):
    summary: str
    key_changes: list[str]
    breaking_changes: list[str] = []
    migration_notes: str = ""
    cve_references: list[str] = []
    severity: str
    tags: list[str]
    worth_tracking: bool = True


class AuthError(Exception):
    """Raised on 401 — invalid API key, stops the pipeline."""


def _call_mistral(prompt: str, api_key: str) -> str:
    client = Mistral(api_key=api_key)
    response = client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=LLM_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    msg = response.choices[0].message
    return str(msg.content) if msg and msg.content else ""


def _analyse_with_model(
    prompt: str,
    api_key: str,
    model_cls: type[BaseModel],
    context: str,
) -> tuple[dict[str, object] | None, str | None]:
    try:
        data = json.loads(_call_mistral(prompt, api_key))
        result = model_cls.model_validate(data)
        return result.model_dump(), None
    except ValidationError as e:
        logger.error("LLM response failed validation for %s: %s", context, e)
        return None, str(e)
    except Exception as e:
        logger.error("LLM call failed for %s: %s", context, e)
        return None, str(e)


def analyse_release(
    release: dict[str, object],
    api_key: str,
) -> tuple[dict[str, object] | None, str | None]:
    repo = str(release.get("repo", ""))
    tag = str(release.get("tag_name", ""))
    name = str(release.get("name", tag))
    body = str(release.get("body", ""))[:4000]
    prompt = RELEASE_ANALYSIS_PROMPT.format(repo=repo, tag=tag, name=name, body=body)
    return _analyse_with_model(prompt, api_key, AnalysisResult, f"{repo}@{tag}")


def analyse_dbt_package_release(
    release: dict[str, object],
    readme: str,
    stale: bool = False,
    use_heuristics: bool = False,
    api_key: str = "",
) -> tuple[dict[str, object] | None, str | None]:
    """Analyse a dbt package release.

    stale=True: no release in >1 year — skip LLM, return README summary only.
    use_heuristics=True: rule-based analysis, no LLM call (for testing).
    """
    from src.fetcher import heuristic_dbt_analysis

    repo = str(release.get("repo", ""))
    tag = str(release.get("tag_name", ""))
    name = str(release.get("name", tag))
    body = str(release.get("body", ""))[:4000]

    if stale:
        purpose = ""
        for para in readme.split("\n\n"):
            clean = para.strip().lstrip("#").strip()
            if len(clean) > 40 and not clean.startswith("!"):
                purpose = clean[:300]
                break
        return {
            "purpose": purpose or f"{repo} dbt package.",
            "summary": f"No release in over a year. Last tag: {tag}.",
            "key_changes": [],
            "is_prod_breaking_bug": False,
            "severity": "none",
            "tags": ["docs-only"],
        }, None

    if use_heuristics:
        result = heuristic_dbt_analysis(release, readme)
        kc = result.get("key_changes", [])
        result["key_changes"] = filter_trivial_changes(kc if isinstance(kc, list) else [])
        return result, None

    prompt = DBT_PACKAGE_ANALYSIS_PROMPT.format(
        repo=repo, tag=tag, name=name, readme=readme[:2000], body=body
    )
    analysis, error = _analyse_with_model(
        prompt, api_key, DbtPackageAnalysisResult, f"{repo}@{tag}"
    )
    if analysis is not None:
        raw_kc = analysis.get("key_changes", [])
        analysis["key_changes"] = filter_trivial_changes(raw_kc if isinstance(raw_kc, list) else [])
    return analysis, error


def analyse_fusion_release(
    release: dict[str, object],
    api_key: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Analyse a dbt-fusion preview release; includes worth_tracking flag."""
    repo = str(release.get("repo", ""))
    tag = str(release.get("tag_name", ""))
    body = str(release.get("body", ""))[:5000]
    prompt = FUSION_RELEASE_ANALYSIS_PROMPT.format(repo=repo, tag=tag, body=body)
    return _analyse_with_model(prompt, api_key, AnalysisResult, f"{repo}@{tag}")


def analyse_lakehouse_release(
    release: dict[str, object],
    api_key: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Analyse a Google Cloud Lakehouse date-window release."""
    tag = str(release.get("tag_name", ""))
    name = str(release.get("name", tag))
    body = str(release.get("body", ""))[:5000]
    prompt = LAKEHOUSE_RELEASE_ANALYSIS_PROMPT.format(tag=tag, name=name, body=body)
    return _analyse_with_model(prompt, api_key, BigQueryAnalysisResult, tag)


def analyse_bigquery_release(
    release: dict[str, object],
    api_key: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Analyse a BigQuery date-window release from Google Cloud Docs."""
    tag = str(release.get("tag_name", ""))
    name = str(release.get("name", tag))
    body = str(release.get("body", ""))[:5000]
    prompt = BIGQUERY_RELEASE_ANALYSIS_PROMPT.format(tag=tag, name=name, body=body)
    return _analyse_with_model(prompt, api_key, BigQueryAnalysisResult, tag)


def analyse_fusion_historical(
    release: dict[str, object],
    api_key: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Analyse the consolidated pre-2026 dbt-fusion historical entry."""
    repo = str(release.get("repo", ""))
    tag = str(release.get("tag_name", ""))
    meta = release.get("_historical_meta", {})
    if not isinstance(meta, dict):
        meta = {}
    prompt = FUSION_HISTORICAL_PROMPT.format(
        version_count=meta.get("version_count", "?"),
        first_version=meta.get("first_version", ""),
        last_version=meta.get("last_version", ""),
        version_list=meta.get("version_list", ""),
        body_sample=str(release.get("body", ""))[:4000],
    )
    return _analyse_with_model(prompt, api_key, AnalysisResult, f"{repo}@{tag}")
