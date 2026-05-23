"""Tests for logslice.summarizer."""
from __future__ import annotations

import pytest

from logslice.parser import LogEntry
from logslice.summarizer import (
    LogSummary,
    SummarizeOptions,
    iter_summary_lines,
    summarize_entries,
)


def _entry(
    msg: str = "hello",
    severity: str = "INFO",
    timestamp: str = "2024-01-01T00:00:00",
) -> LogEntry:
    return LogEntry(timestamp=timestamp, severity=severity, message=msg, raw=msg)


# ---------------------------------------------------------------------------
# SummarizeOptions validation
# ---------------------------------------------------------------------------

class TestSummarizeOptions:
    def test_defaults(self):
        opts = SummarizeOptions()
        assert opts.top_n == 5
        assert opts.include_severity_counts is True
        assert opts.include_time_range is True

    def test_zero_top_n_raises(self):
        with pytest.raises(ValueError, match="top_n"):
            SummarizeOptions(top_n=0)

    def test_negative_top_n_raises(self):
        with pytest.raises(ValueError):
            SummarizeOptions(top_n=-3)


# ---------------------------------------------------------------------------
# summarize_entries
# ---------------------------------------------------------------------------

class TestSummarizeEntries:
    def test_empty_stream_returns_zero_total(self):
        s = summarize_entries([])
        assert s.total == 0

    def test_total_counts_all_entries(self):
        entries = [_entry() for _ in range(7)]
        s = summarize_entries(entries)
        assert s.total == 7

    def test_severity_counts_populated(self):
        entries = [
            _entry(severity="INFO"),
            _entry(severity="ERROR"),
            _entry(severity="INFO"),
        ]
        s = summarize_entries(entries)
        assert s.severity_counts["INFO"] == 2
        assert s.severity_counts["ERROR"] == 1

    def test_severity_counts_disabled(self):
        entries = [_entry(severity="INFO")]
        s = summarize_entries(entries, SummarizeOptions(include_severity_counts=False))
        assert s.severity_counts == {}

    def test_time_range_captured(self):
        entries = [
            _entry(timestamp="2024-01-01T10:00:00"),
            _entry(timestamp="2024-01-01T08:00:00"),
            _entry(timestamp="2024-01-01T12:00:00"),
        ]
        s = summarize_entries(entries)
        assert s.earliest == "2024-01-01T08:00:00"
        assert s.latest == "2024-01-01T12:00:00"

    def test_time_range_disabled(self):
        entries = [_entry(timestamp="2024-01-01T10:00:00")]
        s = summarize_entries(entries, SummarizeOptions(include_time_range=False))
        assert s.earliest is None
        assert s.latest is None

    def test_top_messages_sorted_by_frequency(self):
        entries = [
            _entry(msg="alpha"),
            _entry(msg="beta"),
            _entry(msg="alpha"),
            _entry(msg="gamma"),
            _entry(msg="alpha"),
            _entry(msg="beta"),
        ]
        s = summarize_entries(entries, SummarizeOptions(top_n=2))
        assert len(s.top_messages) == 2
        assert s.top_messages[0] == ("alpha", 3)
        assert s.top_messages[1] == ("beta", 2)

    def test_top_n_limits_results(self):
        entries = [_entry(msg=str(i)) for i in range(10)]
        s = summarize_entries(entries, SummarizeOptions(top_n=3))
        assert len(s.top_messages) == 3

    def test_no_timestamp_entries_skipped_for_range(self):
        entries = [LogEntry(timestamp=None, severity="INFO", message="x", raw="x")]
        s = summarize_entries(entries)
        assert s.earliest is None
        assert s.latest is None


# ---------------------------------------------------------------------------
# iter_summary_lines
# ---------------------------------------------------------------------------

class TestIterSummaryLines:
    def test_total_line_present(self):
        s = LogSummary(total=42)
        lines = list(iter_summary_lines(s))
        assert any("42" in line for line in lines)

    def test_time_range_line_present(self):
        s = LogSummary(total=1, earliest="2024-01-01", latest="2024-01-02")
        lines = list(iter_summary_lines(s))
        assert any("2024-01-01" in line and "2024-01-02" in line for line in lines)

    def test_severity_breakdown_present(self):
        s = LogSummary(total=3, severity_counts={"INFO": 2, "ERROR": 1})
        lines = list(iter_summary_lines(s))
        assert any("INFO" in line for line in lines)
        assert any("ERROR" in line for line in lines)

    def test_top_messages_present(self):
        s = LogSummary(total=2, top_messages=[("disk full", 5)])
        lines = list(iter_summary_lines(s))
        assert any("disk full" in line for line in lines)
        assert any("5x" in line for line in lines)

    def test_long_message_truncated(self):
        long_msg = "x" * 100
        s = LogSummary(total=1, top_messages=[(long_msg, 1)])
        lines = list(iter_summary_lines(s))
        msg_lines = [l for l in lines if "x" * 10 in l]
        assert msg_lines
        assert all(len(l) < 120 for l in msg_lines)
