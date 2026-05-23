"""Integration tests: resampler wired into the pipeline via slice_lines."""
from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO

from logslice.parser import LogEntry
from logslice.resampler import ResampleOptions, resample_entries
from logslice.filter import FilterOptions, filter_entries


def _entry(h: int, m: int, severity: str = "INFO", msg: str = "msg") -> LogEntry:
    ts = datetime(2024, 1, 1, h, m, 0, tzinfo=timezone.utc)
    return LogEntry(timestamp=ts, severity=severity, message=msg, raw=msg)


def _run(
    entries,
    min_severity: str = "DEBUG",
    unit: str = "minute",
    fill_empty: bool = False,
):
    """Filter then resample, returning list of ResampledBucket."""
    filter_opts = FilterOptions(min_severity=min_severity)
    filtered = list(filter_entries(entries, filter_opts))
    resample_opts = ResampleOptions(unit=unit, fill_empty=fill_empty)
    return list(resample_entries(filtered, resample_opts))


class TestPipelineResampler:
    def test_only_filtered_entries_appear_in_buckets(self):
        entries = [
            _entry(10, 0, severity="DEBUG"),
            _entry(10, 0, severity="ERROR"),
            _entry(10, 1, severity="DEBUG"),
        ]
        buckets = _run(entries, min_severity="ERROR")
        total = sum(b.count for b in buckets)
        assert total == 1

    def test_bucket_count_matches_filtered_output(self):
        entries = [
            _entry(10, 0),
            _entry(10, 1),
            _entry(10, 2),
            _entry(10, 3),
        ]
        buckets = _run(entries, unit="hour")
        # all four fall in the same hour bucket
        assert len(buckets) == 1
        assert buckets[0].count == 4

    def test_fill_empty_adds_zero_buckets_between_filtered_entries(self):
        entries = [
            _entry(10, 0, severity="ERROR"),
            _entry(10, 5, severity="ERROR"),
        ]
        buckets = _run(entries, min_severity="ERROR", unit="minute", fill_empty=True)
        assert len(buckets) == 6
        non_empty = [b for b in buckets if b.count > 0]
        assert len(non_empty) == 2

    def test_no_entries_after_filter_yields_no_buckets(self):
        entries = [
            _entry(10, 0, severity="DEBUG"),
            _entry(10, 1, severity="INFO"),
        ]
        buckets = _run(entries, min_severity="ERROR")
        assert buckets == []
