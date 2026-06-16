from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.telegram_notifier import (
    _escape_md,
    _format_releases,
    notify_releases,
    send_notification,
)


class TestEscapeMd:
    def test_escapes_reserved_characters(self):
        assert _escape_md("hello.world") == "hello\\.world"
        assert _escape_md("(test)") == "\\(test\\)"
        assert _escape_md("1+1=2") == "1\\+1\\=2"
        assert _escape_md("a-b") == "a\\-b"
        assert _escape_md("it!") == "it\\!"

    def test_plain_text_unchanged(self):
        assert _escape_md("hello world") == "hello world"

    def test_empty_string(self):
        assert _escape_md("") == ""


class TestFormatReleases:
    def _record(self, repo="org/repo", tag="v1.2.3", summary="A fix.", url="https://example.com"):
        return {"repo": repo, "tag": tag, "html_url": url, "analysis": {"summary": summary}}

    def test_single_record_contains_repo_tag_summary_url(self):
        msg = _format_releases([self._record()])
        assert "org/repo" in msg
        assert "v1" in msg
        assert "example.com" in msg

    def test_full_summary_included(self):
        long_summary = "x" * 500
        msg = _format_releases([self._record(summary=long_summary)])
        assert "x" * 500 in msg

    def test_multiple_records_joined(self):
        r1 = self._record(repo="org/a", tag="v1.0.0")
        r2 = self._record(repo="org/b", tag="v2.0.0")
        msg = _format_releases([r1, r2])
        assert "org/a" in msg
        assert "org/b" in msg

    def test_message_truncated_to_4096(self):
        records = [self._record(summary="s" * 200) for _ in range(30)]
        msg = _format_releases(records)
        assert len(msg) <= 4096

    def test_special_chars_in_repo_escaped(self):
        msg = _format_releases([self._record(repo="org/my.repo")])
        assert "org/my\\.repo" in msg

    def test_missing_analysis_graceful(self):
        record = {"repo": "org/repo", "tag": "v1.0.0", "html_url": "https://x.com", "analysis": None}
        msg = _format_releases([record])
        assert "org/repo" in msg


class TestSendNotification:
    def test_posts_to_telegram_api(self):
        with patch("src.telegram_notifier._http.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            send_notification("tok123", "-100456", "hello")

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert "tok123" in call_kwargs[0][0]
            payload = call_kwargs[1]["json"]
            assert payload["chat_id"] == "-100456"
            assert payload["text"] == "hello"
            assert payload["parse_mode"] == "MarkdownV2"

    def test_api_failure_logs_warning_not_raises(self, caplog):
        with patch("src.telegram_notifier._http.post", side_effect=Exception("timeout")):
            import logging
            with caplog.at_level(logging.WARNING, logger="src.telegram_notifier"):
                send_notification("tok", "chan", "msg")  # must not raise
        assert "timeout" in caplog.text


class TestNotifyReleases:
    def _record(self):
        return {"repo": "org/repo", "tag": "v1.0.0", "html_url": "https://x.com", "analysis": {"summary": "Fix."}}

    def test_empty_records_makes_no_api_call(self):
        with patch("src.telegram_notifier.send_notification") as mock_send:
            notify_releases("tok", "chan", [])
            mock_send.assert_not_called()

    def test_non_empty_records_calls_send(self):
        with patch("src.telegram_notifier.send_notification") as mock_send:
            notify_releases("tok", "chan", [self._record()])
            mock_send.assert_called_once()
            _, channel, message = mock_send.call_args[0]
            assert channel == "chan"
            assert "org/repo" in message
