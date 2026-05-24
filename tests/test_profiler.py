"""Tests for logslice.profiler."""
from __future__ import annotations

from datetime import datetime

import pytest

from logslice.parser import LogEntry
from logslice.profiler import ProfileOptions, ProfileResult, profile_entries


def _entry(
    severity: str = "ERROR",
    ts: datetime | None = None,
    message: str = "msg",
) -> LogEntry:
    return LogEntry(
        raw=f"{severity} {message}",
        timestamp=ts,
        severity=severity,
        message=message,
    )


def _ts(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, second)


class TestProfileOptions:
    def test_defaults(self) -> None:
        opts = ProfileOptions()
        assert opts.bucket_seconds == 60
        assert opts.include_rate is True

    def test_zero_bucket_raises(self) -> None:
        with pytest.raises(ValueError, match="bucket_seconds must be positive"):
            ProfileOptions(bucket_seconds=0)

    def test_negative_bucket_raises(self) -> None:
        with pytest.raises(ValueError, match="bucket_seconds must be positive"):
            ProfileOptions(bucket_seconds=-5)


class TestProfileEntries:
    def test_total_counts_all_entries(self) -> None:
        entries = [_entry("ERROR"), _entry("INFO"), _entry("WARNING")]
        _, result = profile_entries(iter(entries))
        assert result.total == 3

    def test_severity_counts_grouped(self) -> None:
        entries = [_entry("ERROR"), _entry("ERROR"), _entry("INFO")]
        _, result = profile_entries(iter(entries))
        assert result.severity_counts["ERROR"] == 2
        assert result.severity_counts["INFO"] == 1

    def test_unknown_severity_when_none(self) -> None:
        entry = LogEntry(raw="raw", timestamp=None, severity=None, message="x")
        _, result = profile_entries(iter([entry]))
        assert result.severity_counts.get("UNKNOWN", 0) == 1

    def test_entries_are_re_yielded(self) -> None:
        entries = [_entry("INFO"), _entry("ERROR")]
        it, _ = profile_entries(iter(entries))
        assert list(it) == entries

    def test_bucket_counts_populated(self) -> None:
        entries = [
            _entry(ts=_ts(10, 0, 0)),
            _entry(ts=_ts(10, 0, 30)),
            _entry(ts=_ts(10, 1, 0)),
        ]
        _, result = profile_entries(iter(entries), ProfileOptions(bucket_seconds=60))
        assert len(result.bucket_counts) == 2

    def test_bucket_counts_skipped_when_disabled(self) -> None:
        entries = [_entry(ts=_ts(10, 0, 0))]
        _, result = profile_entries(iter(entries), ProfileOptions(include_rate=False))
        assert result.bucket_counts == {}

    def test_no_timestamp_skips_bucket(self) -> None:
        entry = LogEntry(raw="x", timestamp=None, severity="INFO", message="x")
        _, result = profile_entries(iter([entry]))
        assert result.bucket_counts == {}

    def test_top_severity_returns_most_frequent(self) -> None:
        entries = [_entry("ERROR")] * 3 + [_entry("INFO")]
        _, result = profile_entries(iter(entries))
        assert result.top_severity() == "ERROR"

    def test_top_severity_none_when_empty(self) -> None:
        result = ProfileResult()
        assert result.top_severity() is None

    def test_peak_bucket_returns_busiest_slot(self) -> None:
        entries = [
            _entry(ts=_ts(10, 0, 0)),
            _entry(ts=_ts(10, 0, 10)),
            _entry(ts=_ts(10, 1, 0)),
        ]
        _, result = profile_entries(iter(entries), ProfileOptions(bucket_seconds=60))
        peak = result.peak_bucket()
        assert peak == "2024-01-01T10:00:00"

    def test_peak_bucket_none_when_empty(self) -> None:
        result = ProfileResult()
        assert result.peak_bucket() is None
