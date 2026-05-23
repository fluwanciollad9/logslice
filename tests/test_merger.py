"""Tests for logslice.merger."""
from __future__ import annotations

import pytest

from logslice.merger import MergeOptions, merge_entries
from logslice.parser import LogEntry


def _entry(ts: str, severity: str = "INFO", msg: str = "msg") -> LogEntry:
    return LogEntry(timestamp=ts, severity=severity, message=msg, raw="", tags={})


# ---------------------------------------------------------------------------
# MergeOptions validation
# ---------------------------------------------------------------------------

class TestMergeOptions:
    def test_defaults(self):
        opts = MergeOptions()
        assert opts.key == "timestamp"
        assert opts.order == "asc"
        assert opts.tag_source is False

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            MergeOptions(key="message")

    def test_invalid_order_raises(self):
        with pytest.raises(ValueError, match="order"):
            MergeOptions(order="random")


# ---------------------------------------------------------------------------
# merge_entries
# ---------------------------------------------------------------------------

class TestMergeEntries:
    def test_empty_streams_yields_nothing(self):
        result = list(merge_entries([[], []]))
        assert result == []

    def test_single_stream_passthrough(self):
        entries = [_entry("2024-01-01T00:00:01"), _entry("2024-01-01T00:00:02")]
        result = list(merge_entries([entries]))
        assert [e.timestamp for e in result] == [
            "2024-01-01T00:00:01",
            "2024-01-01T00:00:02",
        ]

    def test_two_streams_merged_in_order(self):
        a = [_entry("2024-01-01T00:00:01"), _entry("2024-01-01T00:00:03")]
        b = [_entry("2024-01-01T00:00:02"), _entry("2024-01-01T00:00:04")]
        result = list(merge_entries([a, b]))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps)

    def test_desc_order(self):
        a = [_entry("2024-01-01T00:00:03"), _entry("2024-01-01T00:00:01")]
        b = [_entry("2024-01-01T00:00:04"), _entry("2024-01-01T00:00:02")]
        opts = MergeOptions(order="desc")
        result = list(merge_entries([a, b], opts))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_merge_by_severity(self):
        a = [_entry("t", "DEBUG"), _entry("t", "ERROR")]
        b = [_entry("t", "INFO"), _entry("t", "WARNING")]
        opts = MergeOptions(key="severity")
        result = list(merge_entries([a, b], opts))
        severities = [e.severity for e in result]
        assert severities == ["DEBUG", "INFO", "WARNING", "ERROR"]

    def test_tag_source_annotates_stream_index(self):
        a = [_entry("2024-01-01T00:00:01")]
        b = [_entry("2024-01-01T00:00:02")]
        opts = MergeOptions(tag_source=True)
        result = list(merge_entries([a, b], opts))
        assert result[0].tags["_source"] == "0"
        assert result[1].tags["_source"] == "1"

    def test_tag_source_false_no_annotation(self):
        a = [_entry("2024-01-01T00:00:01")]
        result = list(merge_entries([a]))
        assert "_source" not in (result[0].tags or {})

    def test_three_streams_all_entries_present(self):
        streams = [
            [_entry(f"2024-01-01T00:00:0{i}") for i in [1, 4]],
            [_entry(f"2024-01-01T00:00:0{i}") for i in [2, 5]],
            [_entry(f"2024-01-01T00:00:0{i}") for i in [3, 6]],
        ]
        result = list(merge_entries(streams))
        assert len(result) == 6
