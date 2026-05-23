"""Tests for logslice.resampler."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from logslice.parser import LogEntry
from logslice.resampler import ResampleOptions, ResampledBucket, resample_entries


def _entry(ts: datetime, msg: str = "msg") -> LogEntry:
    return LogEntry(timestamp=ts, severity="INFO", message=msg, raw=msg)


def _ts(h: int = 0, m: int = 0, s: int = 0) -> datetime:
    return datetime(2024, 1, 1, h, m, s, tzinfo=timezone.utc)


class TestResampleOptions:
    def test_defaults(self):
        opts = ResampleOptions()
        assert opts.unit == "minute"
        assert opts.fill_empty is False

    def test_invalid_unit_raises(self):
        with pytest.raises(ValueError, match="unit must be"):
            ResampleOptions(unit="week")

    def test_valid_units_accepted(self):
        for u in ("second", "minute", "hour"):
            assert ResampleOptions(unit=u).unit == u


class TestResampleEntries:
    def test_empty_input_yields_nothing(self):
        result = list(resample_entries([]))
        assert result == []

    def test_entries_without_timestamp_skipped(self):
        e = LogEntry(timestamp=None, severity="INFO", message="x", raw="x")
        result = list(resample_entries([e]))
        assert result == []

    def test_single_entry_produces_one_bucket(self):
        entries = [_entry(_ts(10, 5, 30))]
        buckets = list(resample_entries(entries, ResampleOptions(unit="minute")))
        assert len(buckets) == 1
        assert buckets[0].count == 1
        assert buckets[0].bucket_time == _ts(10, 5, 0)

    def test_entries_in_same_minute_grouped(self):
        entries = [
            _entry(_ts(10, 5, 0)),
            _entry(_ts(10, 5, 30)),
            _entry(_ts(10, 5, 59)),
        ]
        buckets = list(resample_entries(entries, ResampleOptions(unit="minute")))
        assert len(buckets) == 1
        assert buckets[0].count == 3

    def test_entries_in_different_minutes_split(self):
        entries = [
            _entry(_ts(10, 1, 0)),
            _entry(_ts(10, 2, 0)),
            _entry(_ts(10, 3, 0)),
        ]
        buckets = list(resample_entries(entries, ResampleOptions(unit="minute")))
        assert len(buckets) == 3
        assert all(b.count == 1 for b in buckets)

    def test_buckets_sorted_ascending(self):
        entries = [
            _entry(_ts(10, 3, 0)),
            _entry(_ts(10, 1, 0)),
            _entry(_ts(10, 2, 0)),
        ]
        buckets = list(resample_entries(entries, ResampleOptions(unit="minute")))
        times = [b.bucket_time for b in buckets]
        assert times == sorted(times)

    def test_second_resolution(self):
        entries = [
            _entry(_ts(10, 0, 1)),
            _entry(_ts(10, 0, 2)),
        ]
        buckets = list(resample_entries(entries, ResampleOptions(unit="second")))
        assert len(buckets) == 2
        assert buckets[0].bucket_time == _ts(10, 0, 1)

    def test_hour_resolution_groups_across_minutes(self):
        entries = [
            _entry(_ts(10, 0, 0)),
            _entry(_ts(10, 30, 0)),
            _entry(_ts(10, 59, 59)),
        ]
        buckets = list(resample_entries(entries, ResampleOptions(unit="hour")))
        assert len(buckets) == 1
        assert buckets[0].count == 3
        assert buckets[0].bucket_time == _ts(10, 0, 0)

    def test_fill_empty_adds_missing_buckets(self):
        entries = [
            _entry(_ts(10, 0, 0)),
            _entry(_ts(10, 3, 0)),
        ]
        opts = ResampleOptions(unit="minute", fill_empty=True)
        buckets = list(resample_entries(entries, opts))
        assert len(buckets) == 4
        assert buckets[1].count == 0
        assert buckets[2].count == 0

    def test_no_fill_empty_skips_gaps(self):
        entries = [
            _entry(_ts(10, 0, 0)),
            _entry(_ts(10, 3, 0)),
        ]
        opts = ResampleOptions(unit="minute", fill_empty=False)
        buckets = list(resample_entries(entries, opts))
        assert len(buckets) == 2
