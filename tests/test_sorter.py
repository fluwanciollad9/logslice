"""Tests for logslice.sorter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.parser import LogEntry
from logslice.sorter import SortOptions, sort_entries


def _entry(ts: str | None, severity: str = "INFO", message: str = "msg") -> LogEntry:
    parsed = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc) if ts else None
    return LogEntry(timestamp=parsed, severity=severity, message=message, raw=message)


# ---------------------------------------------------------------------------
# SortOptions validation
# ---------------------------------------------------------------------------

class TestSortOptions:
    def test_defaults(self):
        opts = SortOptions()
        assert opts.key == "timestamp"
        assert opts.order == "asc"
        assert opts.stable is True

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid sort key"):
            SortOptions(key="unknown")

    def test_invalid_order_raises(self):
        with pytest.raises(ValueError, match="Invalid sort order"):
            SortOptions(order="random")


# ---------------------------------------------------------------------------
# sort_entries
# ---------------------------------------------------------------------------

class TestSortEntries:
    def test_sort_by_timestamp_asc(self):
        entries = [
            _entry("2024-01-01T12:00:02"),
            _entry("2024-01-01T12:00:00"),
            _entry("2024-01-01T12:00:01"),
        ]
        result = list(sort_entries(entries, SortOptions(key="timestamp", order="asc")))
        timestamps = [e.timestamp.isoformat() for e in result]
        assert timestamps == sorted(timestamps)

    def test_sort_by_timestamp_desc(self):
        entries = [
            _entry("2024-01-01T12:00:00"),
            _entry("2024-01-01T12:00:02"),
            _entry("2024-01-01T12:00:01"),
        ]
        result = list(sort_entries(entries, SortOptions(key="timestamp", order="desc")))
        timestamps = [e.timestamp.isoformat() for e in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_sort_by_severity_asc(self):
        entries = [
            _entry("2024-01-01T00:00:00", severity="WARNING"),
            _entry("2024-01-01T00:00:01", severity="DEBUG"),
            _entry("2024-01-01T00:00:02", severity="ERROR"),
        ]
        result = list(sort_entries(entries, SortOptions(key="severity", order="asc")))
        assert [e.severity for e in result] == ["DEBUG", "ERROR", "WARNING"]

    def test_sort_by_message_asc(self):
        entries = [
            _entry("2024-01-01T00:00:00", message="zebra"),
            _entry("2024-01-01T00:00:01", message="apple"),
            _entry("2024-01-01T00:00:02", message="mango"),
        ]
        result = list(sort_entries(entries, SortOptions(key="message", order="asc")))
        assert [e.message for e in result] == ["apple", "mango", "zebra"]

    def test_none_timestamp_sorts_first_asc(self):
        entries = [
            _entry("2024-01-01T12:00:00"),
            _entry(None),
        ]
        result = list(sort_entries(entries, SortOptions(key="timestamp", order="asc")))
        assert result[0].timestamp is None

    def test_default_opts_used_when_none_passed(self):
        entries = [
            _entry("2024-01-01T12:00:01"),
            _entry("2024-01-01T12:00:00"),
        ]
        result = list(sort_entries(entries))
        assert result[0].timestamp < result[1].timestamp

    def test_empty_input_returns_empty(self):
        assert list(sort_entries([], SortOptions())) == []
