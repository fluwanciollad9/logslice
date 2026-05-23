"""Integration tests: merger wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from logslice.filter import FilterOptions
from logslice.merger import MergeOptions, merge_entries
from logslice.parser import LogEntry


def _entry(ts: str, severity: str = "INFO", msg: str = "msg") -> LogEntry:
    return LogEntry(timestamp=ts, severity=severity, message=msg, raw="", tags={})


def _run(
    streams: List[List[LogEntry]],
    merge_opts: MergeOptions | None = None,
    filter_opts: FilterOptions | None = None,
) -> List[LogEntry]:
    from logslice.filter import filter_entries

    merged = merge_entries(streams, merge_opts)
    if filter_opts is not None:
        merged = filter_entries(merged, filter_opts)
    return list(merged)


class TestPipelineMerger:
    def test_merge_then_filter_by_severity(self):
        a = [_entry("2024-01-01T00:00:01", "DEBUG"), _entry("2024-01-01T00:00:03", "ERROR")]
        b = [_entry("2024-01-01T00:00:02", "INFO"), _entry("2024-01-01T00:00:04", "WARNING")]
        result = _run([a, b], filter_opts=FilterOptions(min_severity="WARNING"))
        severities = {e.severity for e in result}
        assert severities <= {"WARNING", "ERROR", "CRITICAL"}

    def test_merged_output_count_equals_sum_of_inputs(self):
        a = [_entry(f"2024-01-01T00:00:0{i}") for i in range(1, 4)]
        b = [_entry(f"2024-01-01T00:00:0{i}") for i in range(4, 7)]
        result = _run([a, b])
        assert len(result) == 6

    def test_tag_source_survives_filter(self):
        a = [_entry("2024-01-01T00:00:01", "ERROR")]
        b = [_entry("2024-01-01T00:00:02", "ERROR")]
        opts = MergeOptions(tag_source=True)
        result = _run([a, b], merge_opts=opts, filter_opts=FilterOptions(min_severity="ERROR"))
        assert all("_source" in (e.tags or {}) for e in result)
