"""The email Cloud Function must use the portfolio palette (no legacy purple, no gradient)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

_MAIN = Path(__file__).parent.parent / "functions" / "email" / "main.py"
_LEGACY = ("#5b5fc7", "#8b5cf6", "#ede9fe", "#f5f3ff", "linear-gradient")


@pytest.fixture(scope="module")
def email_main() -> ModuleType:
    stubs = ("functions_framework", "flask", "google.cloud", "google.cloud.secretmanager")
    saved = {name: sys.modules.get(name) for name in stubs}
    for name in stubs:
        sys.modules[name] = MagicMock()
    try:
        spec = importlib.util.spec_from_file_location("email_main", _MAIN)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _release(severity: str) -> dict:
    return {
        "repo": "dbt-labs/dbt-core",
        "tag": "v2.0.5",
        "html_url": "https://example.com",
        "analysis": {"severity": severity, "summary": "Fix.", "key_changes": ["a", "b"]},
    }


def test_digest_has_no_legacy_colours(email_main: ModuleType) -> None:
    html = email_main._build_html([_release("high"), _release("none")])
    assert not [c for c in _LEGACY if c in html]
    assert "#f5f0e8" in html and "Playfair Display" in html and "Georgia" in html


def test_failure_email_has_no_legacy_colours(email_main: ModuleType) -> None:
    html = email_main._fail_html("boom", "o/r")
    assert not [c for c in _LEGACY if c in html]
    assert "light only" in html


def test_high_badge_uses_site_pair(email_main: ModuleType) -> None:
    html = email_main._render_card(_release("high"))
    assert "background:#f8e3cd;color:#8a4300" in html


def test_unknown_severity_falls_back_to_none(email_main: ModuleType) -> None:
    html = email_main._render_card(_release("banana"))
    assert "background:#ece6dc;color:#5d6677" in html
