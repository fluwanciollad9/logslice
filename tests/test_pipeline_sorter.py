"""Integration tests: sorter wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.sorter import SortOptions


def _entry(ts: str, severity: str = "INFO", message: str = "msg") -> LogEntry:
    parsed = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    return LogEntry(timestamp=parsed, severity=severity, message=message, raw=message)


def _run(entries: List[LogEntry], sort_opts: SortOptions | None) -> List[LogEntry]:
    opts = PipelineOptions(sort=sort_opts)
    return list(run_pipeline(iter(entries), opts))


class TestPipelineSorter:
    def test_sort_disabled_by_default(self):
        entries = [
            _entry("2024-01-01T12:00:02"),
            _entry("2024-01-01T12:00:00"),
        ]
        result = _run(entries, sort_opts=None)
        # order unchanged when sort not configured
        assert result[0].timestamp > result[1].timestamp

    def test_sort_asc_orders_correctly(self):
        entries = [
            _entry("2024-01-01T12:00:03"),
            _entry("2024-01-01T12:00:01"),
            _entry("2024-01-01T12:00:02"),
        ]
        result = _run(entries, SortOptions(key="timestamp", order="asc"))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps)

    def test_sort_desc_orders_correctly(self):
        entries = [
            _entry("2024-01-01T12:00:01"),
            _entry("2024-01-01T12:00:03"),
            _entry("2024-01-01T12:00:02"),
        ]
        result = _run(entries, SortOptions(key="timestamp", order="desc"))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_sort_preserves_all_entries(self):
        entries = [_entry(f"2024-01-01T12:00:0{i}") for i in range(5)]
        result = _run(entries, SortOptions(key="timestamp", order="asc"))
        assert len(result) == len(entries)
