"""Tests for logslice.zipper."""

from __future__ import annotations

import pytest

from logslice.parser import LogEntry
from logslice.zipper import ZipOptions, zip_entries


def _entry(ts: str, severity: str = "INFO", message: str = "msg") -> LogEntry:
    return LogEntry(timestamp=ts, severity=severity, message=message, raw="")


# ---------------------------------------------------------------------------
# ZipOptions validation
# ---------------------------------------------------------------------------

class TestZipOptions:
    def test_defaults(self):
        opts = ZipOptions()
        assert opts.key == "timestamp"
        assert opts.order == "asc"
        assert opts.tag_left == ""
        assert opts.tag_right == ""

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            ZipOptions(key="message")

    def test_invalid_order_raises(self):
        with pytest.raises(ValueError, match="order"):
            ZipOptions(order="random")


# ---------------------------------------------------------------------------
# zip_entries behaviour
# ---------------------------------------------------------------------------

class TestZipEntries:
    def test_empty_both_yields_nothing(self):
        assert list(zip_entries([], [])) == []

    def test_empty_left_yields_right(self):
        right = [_entry("2024-01-01T00:00:01")]
        result = list(zip_entries([], right))
        assert len(result) == 1

    def test_empty_right_yields_left(self):
        left = [_entry("2024-01-01T00:00:01")]
        result = list(zip_entries(left, []))
        assert len(result) == 1

    def test_interleaved_by_timestamp_asc(self):
        left = [_entry("2024-01-01T00:00:01"), _entry("2024-01-01T00:00:03")]
        right = [_entry("2024-01-01T00:00:02"), _entry("2024-01-01T00:00:04")]
        result = list(zip_entries(left, right))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps)

    def test_interleaved_by_timestamp_desc(self):
        left = [_entry("2024-01-01T00:00:03"), _entry("2024-01-01T00:00:01")]
        right = [_entry("2024-01-01T00:00:04"), _entry("2024-01-01T00:00:02")]
        opts = ZipOptions(order="desc")
        result = list(zip_entries(left, right, opts))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_total_count_equals_sum_of_inputs(self):
        left = [_entry(f"2024-01-01T00:00:0{i}") for i in range(3)]
        right = [_entry(f"2024-01-01T00:00:0{i}") for i in range(3, 6)]
        result = list(zip_entries(left, right))
        assert len(result) == 6

    def test_tag_left_applied(self):
        left = [_entry("2024-01-01T00:00:01")]
        opts = ZipOptions(tag_left="src-a")
        result = list(zip_entries(left, [], opts))
        assert "src-a" in (result[0].tags or [])

    def test_tag_right_applied(self):
        right = [_entry("2024-01-01T00:00:01")]
        opts = ZipOptions(tag_right="src-b")
        result = list(zip_entries([], right, opts))
        assert "src-b" in (result[0].tags or [])

    def test_no_tag_when_label_empty(self):
        left = [_entry("2024-01-01T00:00:01")]
        result = list(zip_entries(left, []))
        assert not result[0].tags

    def test_zip_by_severity_asc(self):
        left = [_entry("t1", severity="ERROR")]
        right = [_entry("t2", severity="DEBUG")]
        opts = ZipOptions(key="severity")
        result = list(zip_entries(left, right, opts))
        assert result[0].severity == "DEBUG"
        assert result[1].severity == "ERROR"
