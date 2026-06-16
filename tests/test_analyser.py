import json
from unittest.mock import MagicMock, call, patch

from mistralai.client.models import UserMessageTypedDict

from src.analyser import (
    _call_mistral,
    analyse_bigquery_release,
    analyse_dbt_package_release,
    analyse_fusion_historical,
    analyse_fusion_release,
    analyse_lakehouse_release,
    analyse_release,
    filter_trivial_changes,
)

_VALID_ANALYSIS = {
    "summary": "This release fixes several bugs.",
    "key_changes": ["Fixed bug A", "Fixed bug B"],
    "cve_references": [],
    "severity": "none",
    "tags": ["bug-fix"],
}


def _make_release(body: str = "Fixed bugs.") -> dict[str, object]:
    return {"repo": "owner/repo", "tag_name": "v1.0.0", "name": "Release 1.0.0", "body": body}


def _mock_mistral_client(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.complete.return_value = response
    return client


def test_happy_path() -> None:
    mock_client = _mock_mistral_client(json.dumps(_VALID_ANALYSIS))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_release(_make_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["summary"] == _VALID_ANALYSIS["summary"]
    assert analysis["severity"] == "none"


def test_invalid_json_returns_none() -> None:
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client("not json }{")):
        analysis, error = analyse_release(_make_release(), "fake-key")
    assert analysis is None
    assert error is not None


def test_cve_detection() -> None:
    body = "Fixes CVE-2026-12345 and CVE-2026-99999."
    payload = {**_VALID_ANALYSIS, "cve_references": ["CVE-2026-12345"], "severity": "high"}
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client(json.dumps(payload))):
        analysis, error = analyse_release(_make_release(body), "fake-key")
    assert error is None
    assert analysis is not None
    assert "CVE-2026-12345" in analysis["cve_references"]
    assert analysis["severity"] == "high"


def test_exception_returns_none() -> None:
    client = MagicMock()
    client.chat.complete.side_effect = Exception("timeout")
    with patch("src.analyser.Mistral", return_value=client):
        analysis, error = analyse_release(_make_release(), "fake-key")
    assert analysis is None
    assert "timeout" in (error or "")


def test_call_mistral_returns_string() -> None:
    client = MagicMock()
    client.chat.complete.return_value.choices[0].message.content = '{"ok": true}'
    with patch("src.analyser.Mistral", return_value=client):
        result = _call_mistral("some prompt", "fake-key")
    assert result == '{"ok": true}'


def test_call_mistral_sends_typed_user_message() -> None:
    client = MagicMock()
    client.chat.complete.return_value.choices[0].message.content = '{"ok": true}'
    with patch("src.analyser.Mistral", return_value=client):
        _call_mistral("hello world", "fake-key")
    kwargs = client.chat.complete.call_args.kwargs
    messages = kwargs["messages"]
    assert len(messages) == 1
    msg = messages[0]
    assert msg == UserMessageTypedDict(role="user", content="hello world")
    assert msg["role"] == "user"
    assert msg["content"] == "hello world"


# ── analyse_fusion_release ───────────────────────────────────────────────────

_FUSION_ANALYSIS = {
    **_VALID_ANALYSIS,
    "worth_tracking": True,
    "breaking_changes": [],
    "migration_notes": "",
}


def _make_fusion_release() -> dict[str, object]:
    return {
        "repo": "dbt-labs/dbt-fusion",
        "tag_name": "2.0.0-preview.177",
        "body": "Released January 20, 2026\n\n### Features\n\n- Add Snowflake adapter",
    }


def test_fusion_release_worth_tracking_true() -> None:
    mock_client = _mock_mistral_client(json.dumps(_FUSION_ANALYSIS))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_fusion_release(_make_fusion_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["worth_tracking"] is True


def test_fusion_release_worth_tracking_false() -> None:
    payload = {**_FUSION_ANALYSIS, "worth_tracking": False, "key_changes": []}
    mock_client = _mock_mistral_client(json.dumps(payload))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_fusion_release(_make_fusion_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["worth_tracking"] is False


def test_fusion_release_invalid_json_returns_none() -> None:
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client("bad json")):
        analysis, error = analyse_fusion_release(_make_fusion_release(), "fake-key")
    assert analysis is None
    assert error is not None


def test_fusion_release_exception_returns_none() -> None:
    client = MagicMock()
    client.chat.complete.side_effect = Exception("network error")
    with patch("src.analyser.Mistral", return_value=client):
        analysis, error = analyse_fusion_release(_make_fusion_release(), "fake-key")
    assert analysis is None
    assert "network error" in (error or "")


# ── analyse_fusion_historical ────────────────────────────────────────────────


def _make_historical_release() -> dict[str, object]:
    return {
        "repo": "dbt-labs/dbt-fusion",
        "tag_name": "2.0.0-pre-2026",
        "body": "### 2.0.0-preview.4\nFirst release\n\n---\n\n### 2.0.0-preview.5\nBigQuery",
        "_historical_meta": {
            "version_count": 10,
            "first_version": "2.0.0-preview.4",
            "last_version": "2.0.0-preview.5",
            "version_list": "- 2.0.0-preview.4 (2025-10-01)\n- 2.0.0-preview.5 (2025-11-20)",
        },
    }


def test_fusion_historical_returns_worth_tracking_true() -> None:
    payload = {**_FUSION_ANALYSIS, "worth_tracking": True}
    mock_client = _mock_mistral_client(json.dumps(payload))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_fusion_historical(_make_historical_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["worth_tracking"] is True


def test_fusion_historical_invalid_json_returns_none() -> None:
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client("not json")):
        analysis, error = analyse_fusion_historical(_make_historical_release(), "fake-key")
    assert analysis is None
    assert error is not None


def test_fusion_historical_bad_meta_does_not_crash() -> None:
    release = {**_make_historical_release(), "_historical_meta": "bad"}
    payload = {**_FUSION_ANALYSIS, "worth_tracking": True}
    mock_client = _mock_mistral_client(json.dumps(payload))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_fusion_historical(release, "fake-key")
    assert error is None
    assert analysis is not None


# ── BigQuery / Lakehouse analyser ────────────────────────────────────────────

_BQ_ANALYSIS = {
    "summary": "Python UDFs are now GA.",
    "key_changes": ["[GA][Python UDFs] Now generally available."],
    "breaking_changes": [],
    "migration_notes": "",
    "cost_and_performance_impact": "",
    "severity": "low",
    "tags": ["ga-migration"],
}


def _make_gcp_release(tag: str = "2026-05-20") -> dict[str, object]:
    return {
        "repo": "google/bigquery",
        "tag_name": tag,
        "name": f"BigQuery — {tag}",
        "body": "Feature Python UDFs are now Generally Available (GA).",
        "published_at": f"{tag}T00:00:00+00:00",
    }


def test_bigquery_happy_path() -> None:
    mock_client = _mock_mistral_client(json.dumps(_BQ_ANALYSIS))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_bigquery_release(_make_gcp_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["severity"] == "low"
    assert analysis["tags"] == ["ga-migration"]


def test_bigquery_invalid_json_returns_none() -> None:
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client("not json")):
        analysis, error = analyse_bigquery_release(_make_gcp_release(), "fake-key")
    assert analysis is None
    assert error is not None


def test_bigquery_coerces_dict_in_breaking_changes() -> None:
    payload = {
        **_BQ_ANALYSIS,
        "breaking_changes": [{"text": "ActionValue changes from INT to FLOAT"}],
    }
    mock_client = _mock_mistral_client(json.dumps(payload))
    with patch("src.analyser.Mistral", return_value=mock_client):
        analysis, error = analyse_bigquery_release(_make_gcp_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert isinstance(analysis["breaking_changes"][0], str)


def test_lakehouse_happy_path() -> None:
    payload = {**_BQ_ANALYSIS, "tags": ["iceberg", "catalog"]}
    mock_client = _mock_mistral_client(json.dumps(payload))
    with patch("src.analyser.Mistral", return_value=mock_client):
        release = {**_make_gcp_release(), "repo": "google/lakehouse"}
        analysis, error = analyse_lakehouse_release(release, "fake-key")
    assert error is None
    assert analysis is not None
    assert "iceberg" in analysis["tags"]


def test_lakehouse_invalid_json_returns_none() -> None:
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client("not json")):
        release = {**_make_gcp_release(), "repo": "google/lakehouse"}
        analysis, error = analyse_lakehouse_release(release, "fake-key")
    assert analysis is None
    assert error is not None


# ── Validation de l'output LLM ───────────────────────────────────────────────


def test_analyse_release_missing_required_field_returns_error() -> None:
    """Le LLM oublie 'severity' → ValidationError → (None, message d'erreur)."""
    payload = {k: v for k, v in _VALID_ANALYSIS.items() if k != "severity"}
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client(json.dumps(payload))):
        analysis, error = analyse_release(_make_release(), "fake-key")
    assert analysis is None
    assert error is not None
    assert "severity" in error


def test_analyse_release_optional_fields_default_when_absent() -> None:
    """Champs optionnels absents de l'output LLM → valeurs par défaut."""
    minimal = {"summary": "Bug fixes.", "key_changes": ["Fix A"], "severity": "low", "tags": []}
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client(json.dumps(minimal))):
        analysis, error = analyse_release(_make_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["breaking_changes"] == []
    assert analysis["migration_notes"] == ""
    assert analysis["cve_references"] == []
    assert analysis["worth_tracking"] is True


def test_analyse_release_preserves_all_llm_fields() -> None:
    """Tous les champs de l'output LLM sont bien retournés dans le dict final."""
    payload = {**_VALID_ANALYSIS, "breaking_changes": ["API removed"], "migration_notes": "Use v2."}
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client(json.dumps(payload))):
        analysis, error = analyse_release(_make_release(), "fake-key")
    assert error is None
    assert analysis is not None
    assert analysis["breaking_changes"] == ["API removed"]
    assert analysis["migration_notes"] == "Use v2."
    assert analysis["summary"] == _VALID_ANALYSIS["summary"]
    assert analysis["tags"] == _VALID_ANALYSIS["tags"]


# ── filter_trivial_changes ───────────────────────────────────────────────────


def test_filter_trivial_changes_removes_cosmetic_entries() -> None:
    changes = ["Fix critical bug", "chore: bump version", "Update readme", "Add Python 3.12"]
    result = filter_trivial_changes(changes)
    assert "Fix critical bug" in result
    assert "Add Python 3.12" in result
    assert not any("chore" in c.lower() or "readme" in c.lower() for c in result)


def test_filter_trivial_changes_keeps_all_meaningful() -> None:
    changes = ["Breaking: remove deprecated API", "Add Snowflake adapter", "Fix auth bug"]
    assert filter_trivial_changes(changes) == changes


def test_filter_trivial_changes_ignores_non_strings() -> None:
    changes: list[str] = []  # type: ignore[assignment]
    mixed: list[object] = ["Valid change", 42, None, {"key": "value"}]
    result = filter_trivial_changes(mixed)  # type: ignore[arg-type]
    assert result == ["Valid change"]


# ── analyse_dbt_package_release ──────────────────────────────────────────────


def _make_dbt_release(tag: str = "v1.2.0") -> dict[str, object]:
    return {"repo": "dbt-labs/dbt-utils", "tag_name": tag, "name": tag, "body": "Bug fixes."}


def test_dbt_stale_returns_summary_without_llm_call() -> None:
    """stale=True → aucun appel LLM, résumé extrait du README."""
    readme = "dbt-utils is a package for common macros.\n\nInstallation: add to packages.yml."
    with patch("src.analyser.Mistral") as mock_cls:
        analysis, error = analyse_dbt_package_release(
            _make_dbt_release(), readme=readme, stale=True
        )
    mock_cls.assert_not_called()
    assert error is None
    assert analysis is not None
    assert analysis["severity"] == "none"
    assert analysis["is_prod_breaking_bug"] is False
    assert "No release in over a year" in str(analysis["summary"])


def test_dbt_llm_output_trivial_changes_are_filtered() -> None:
    """Les trivial changes dans l'output LLM sont filtrées avant le retour."""
    payload = {
        "purpose": "Common macros for dbt.",
        "summary": "Minor release.",
        "key_changes": ["Fix critical bug", "chore: bump changelog", "Update docs"],
        "is_prod_breaking_bug": False,
        "severity": "low",
        "tags": ["bug-fix"],
    }
    with patch("src.analyser.Mistral", return_value=_mock_mistral_client(json.dumps(payload))):
        analysis, error = analyse_dbt_package_release(
            _make_dbt_release(), readme="", api_key="fake-key"
        )
    assert error is None
    assert analysis is not None
    key_changes = analysis["key_changes"]
    assert isinstance(key_changes, list)
    assert "Fix critical bug" in key_changes
    assert not any("chore" in c.lower() or "docs" in c.lower() for c in key_changes)
