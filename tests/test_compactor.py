"""Tests for logslice.compactor."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.compactor import CompactOptions, compact_entries
from logslice.parser import LogEntry


def _entry(
    message: str = "hello",
    severity: str = "INFO",
    ts_offset: float = 0.0,
    tags: dict | None = None,
) -> LogEntry:
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    return LogEntry(
        timestamp=base + timedelta(seconds=ts_offset),
        severity=severity,
        message=message,
        raw=f"2024-01-01 12:00:00 {severity} {message}",
        tags=tags or {},
    )


# ---------------------------------------------------------------------------
# CompactOptions validation
# ---------------------------------------------------------------------------

class TestCompactOptions:
    def test_defaults(self):
        o = CompactOptions()
        assert o.max_gap_seconds == 5.0
        assert o.case_sensitive is False
        assert o.repeat_tag == "repeated"

    def test_negative_gap_raises(self):
        with pytest.raises(ValueError, match="max_gap_seconds"):
            CompactOptions(max_gap_seconds=-1)

    def test_empty_repeat_tag_raises(self):
        with pytest.raises(ValueError, match="repeat_tag"):
            CompactOptions(repeat_tag="")


# ---------------------------------------------------------------------------
# compact_entries behaviour
# ---------------------------------------------------------------------------

class TestCompactEntries:
    def test_empty_input_yields_nothing(self):
        assert list(compact_entries([])) == []

    def test_single_entry_no_tag(self):
        result = list(compact_entries([_entry()]))
        assert len(result) == 1
        assert "repeated" not in result[0].tags

    def test_two_identical_entries_merged(self):
        entries = [_entry(ts_offset=0), _entry(ts_offset=1)]
        result = list(compact_entries(entries))
        assert len(result) == 1
        assert result[0].tags["repeated"] == "2"

    def test_three_identical_entries_merged(self):
        entries = [_entry(ts_offset=i) for i in range(3)]
        result = list(compact_entries(entries))
        assert len(result) == 1
        assert result[0].tags["repeated"] == "3"

    def test_different_messages_not_merged(self):
        entries = [_entry("foo"), _entry("bar")]
        result = list(compact_entries(entries))
        assert len(result) == 2

    def test_different_severity_not_merged(self):
        entries = [_entry(severity="INFO"), _entry(severity="ERROR")]
        result = list(compact_entries(entries))
        assert len(result) == 2

    def test_gap_too_large_breaks_run(self):
        opts = CompactOptions(max_gap_seconds=2.0)
        entries = [_entry(ts_offset=0), _entry(ts_offset=10)]
        result = list(compact_entries(entries, opts))
        assert len(result) == 2
        assert "repeated" not in result[0].tags

    def test_case_insensitive_by_default(self):
        entries = [_entry("Hello"), _entry("hello")]
        result = list(compact_entries(entries))
        assert len(result) == 1
        assert result[0].tags["repeated"] == "2"

    def test_case_sensitive_option(self):
        opts = CompactOptions(case_sensitive=True)
        entries = [_entry("Hello"), _entry("hello")]
        result = list(compact_entries(entries, opts))
        assert len(result) == 2

    def test_custom_repeat_tag(self):
        opts = CompactOptions(repeat_tag="count")
        entries = [_entry(ts_offset=0), _entry(ts_offset=1)]
        result = list(compact_entries(entries, opts))
        assert "count" in result[0].tags

    def test_existing_tags_preserved(self):
        e = _entry(tags={"source": "app"})
        entries = [e, _entry(ts_offset=1)]
        result = list(compact_entries(entries))
        assert result[0].tags["source"] == "app"
        assert result[0].tags["repeated"] == "2"
