"""Tests for logslice.truncator."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.truncator import (
    TruncateOptions,
    _truncate,
    truncate_entry,
    truncate_entries,
)

_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _entry(message: str = "hello world", raw: str | None = None) -> LogEntry:
    return LogEntry(timestamp=_TS, severity="INFO", message=message, raw=raw)


# ---------------------------------------------------------------------------
# TruncateOptions validation
# ---------------------------------------------------------------------------

class TestTruncateOptions:
    def test_defaults(self):
        opts = TruncateOptions()
        assert opts.max_length == 200
        assert opts.ellipsis == "..."
        assert opts.fields == ["message"]

    def test_zero_max_length_raises(self):
        with pytest.raises(ValueError, match="max_length"):
            TruncateOptions(max_length=0)

    def test_negative_max_length_raises(self):
        with pytest.raises(ValueError):
            TruncateOptions(max_length=-5)

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown fields"):
            TruncateOptions(fields=["message", "severity"])

    def test_valid_raw_field(self):
        opts = TruncateOptions(fields=["raw"])
        assert opts.fields == ["raw"]


# ---------------------------------------------------------------------------
# _truncate helper
# ---------------------------------------------------------------------------

class TestTruncateHelper:
    def test_short_text_unchanged(self):
        assert _truncate("hi", 10, "...") == "hi"

    def test_exact_length_unchanged(self):
        assert _truncate("hello", 5, "...") == "hello"

    def test_long_text_truncated(self):
        result = _truncate("hello world", 8, "...")
        assert result == "hello..."
        assert len(result) == 8

    def test_custom_ellipsis(self):
        result = _truncate("abcdef", 4, "~")
        assert result == "abc~"

    def test_max_length_shorter_than_ellipsis(self):
        result = _truncate("abcdef", 2, "...")
        assert len(result) <= 2


# ---------------------------------------------------------------------------
# truncate_entry
# ---------------------------------------------------------------------------

class TestTruncateEntry:
    def test_short_message_unchanged(self):
        e = _entry("short")
        result = truncate_entry(e, TruncateOptions(max_length=50))
        assert result.message == "short"

    def test_long_message_truncated(self):
        e = _entry("x" * 300)
        result = truncate_entry(e, TruncateOptions(max_length=10))
        assert len(result.message) == 10
        assert result.message.endswith("...")

    def test_raw_field_truncated_when_selected(self):
        e = _entry(raw="y" * 300)
        opts = TruncateOptions(max_length=20, fields=["raw"])
        result = truncate_entry(e, opts)
        assert len(result.raw) == 20
        assert result.message == e.message  # message untouched

    def test_timestamp_and_severity_preserved(self):
        e = _entry("some message")
        result = truncate_entry(e, TruncateOptions())
        assert result.timestamp == _TS
        assert result.severity == "INFO"

    def test_none_message_skipped(self):
        e = LogEntry(timestamp=_TS, severity="DEBUG", message=None, raw=None)
        result = truncate_entry(e, TruncateOptions())
        assert result.message is None


# ---------------------------------------------------------------------------
# truncate_entries
# ---------------------------------------------------------------------------

class TestTruncateEntries:
    def test_yields_all_entries(self):
        entries = [_entry(f"msg {i}") for i in range(5)]
        result = list(truncate_entries(entries))
        assert len(result) == 5

    def test_default_opts_used_when_none(self):
        long_msg = "z" * 300
        entries = [_entry(long_msg)]
        result = list(truncate_entries(entries, opts=None))
        assert len(result[0].message) == 200

    def test_returns_iterator(self):
        import types
        result = truncate_entries([])
        assert isinstance(result, types.GeneratorType)
