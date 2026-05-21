"""Tests for logslice.highlighter."""
from datetime import datetime, timezone

import pytest

from logslice.highlighter import (
    HighlightOptions,
    _highlight_keywords,
    highlight_entry,
    highlight_entries,
)
from logslice.parser import LogEntry

_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _entry(message: str = "hello world", severity: str = "info") -> LogEntry:
    return LogEntry(timestamp=_TS, severity=severity, message=message, raw=message)


class TestHighlightOptions:
    def test_defaults(self):
        opts = HighlightOptions()
        assert opts.keywords == []
        assert opts.color is True
        assert opts.case_sensitive is False

    def test_invalid_keywords_raises(self):
        with pytest.raises(TypeError):
            HighlightOptions(keywords="error")  # type: ignore[arg-type]


class TestHighlightKeywords:
    def test_no_keywords_returns_original(self):
        result = _highlight_keywords("hello error world", [], color=True, case_sensitive=False)
        assert result == "hello error world"

    def test_color_false_returns_original(self):
        result = _highlight_keywords("hello error world", ["error"], color=False, case_sensitive=False)
        assert result == "hello error world"

    def test_keyword_wrapped_in_ansi(self):
        result = _highlight_keywords("hello error world", ["error"], color=True, case_sensitive=False)
        assert "error" in result
        assert "\033[" in result
        assert "\033[0m" in result

    def test_case_insensitive_match(self):
        result = _highlight_keywords("Hello ERROR world", ["error"], color=True, case_sensitive=False)
        assert "\033[" in result
        assert "ERROR" in result

    def test_case_sensitive_no_match(self):
        result = _highlight_keywords("Hello ERROR world", ["error"], color=True, case_sensitive=True)
        assert "\033[" not in result

    def test_multiple_occurrences_all_highlighted(self):
        result = _highlight_keywords("err err err", ["err"], color=True, case_sensitive=False)
        assert result.count("\033[0m") == 3

    def test_multiple_keywords(self):
        result = _highlight_keywords("foo bar baz", ["foo", "baz"], color=True, case_sensitive=False)
        assert result.count("\033[0m") == 2


class TestHighlightEntry:
    def test_message_highlighted(self):
        entry = _entry("connection timeout occurred")
        opts = HighlightOptions(keywords=["timeout"])
        result = highlight_entry(entry, opts)
        assert "\033[" in result.message
        assert result.timestamp == entry.timestamp
        assert result.severity == entry.severity
        assert result.raw == entry.raw

    def test_no_keywords_message_unchanged(self):
        entry = _entry("plain message")
        opts = HighlightOptions(keywords=[])
        result = highlight_entry(entry, opts)
        assert result.message == "plain message"


class TestHighlightEntries:
    def test_yields_all_entries(self):
        entries = [_entry(f"msg {i}") for i in range(5)]
        opts = HighlightOptions(keywords=["msg"])
        results = list(highlight_entries(entries, opts))
        assert len(results) == 5

    def test_empty_input(self):
        results = list(highlight_entries([], HighlightOptions(keywords=["x"])))
        assert results == []
