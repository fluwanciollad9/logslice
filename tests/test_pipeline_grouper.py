"""Integration tests: grouper wired into the pipeline."""
from __future__ import annotations

from datetime import datetime

from logslice.grouper import GroupOptions, iter_group_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(severity: str = "INFO", message: str = "msg") -> LogEntry:
    return LogEntry(
        raw=f"{severity} {message}",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
    )


def _run(entries, filter_opts=None, group_opts=None):
    """Filter then group, mirroring pipeline usage."""
    filtered = list(filter_entries(entries, filter_opts or FilterOptions()))
    return dict(iter_group_entries(filtered, group_opts or GroupOptions()))


class TestPipelineGrouper:
    def test_only_filtered_entries_appear_in_groups(self):
        entries = [_entry("ERROR"), _entry("INFO"), _entry("ERROR")]
        fopts = FilterOptions(min_severity="ERROR")
        result = _run(entries, filter_opts=fopts)
        assert set(result.keys()) == {"ERROR"}
        assert len(result["ERROR"]) == 2

    def test_group_counts_match_filter_output(self):
        entries = [_entry("DEBUG")] * 3 + [_entry("WARNING")] * 2
        fopts = FilterOptions(min_severity="WARNING")
        result = _run(entries, filter_opts=fopts)
        total = sum(len(v) for v in result.values())
        filtered_count = len(list(filter_entries(entries, fopts)))
        assert total == filtered_count

    def test_empty_after_filter_gives_empty_groups(self):
        entries = [_entry("DEBUG"), _entry("INFO")]
        fopts = FilterOptions(min_severity="ERROR")
        result = _run(entries, filter_opts=fopts)
        assert result == {}

    def test_group_keys_are_sorted(self):
        entries = [_entry("WARNING"), _entry("ERROR"), _entry("INFO")]
        result = _run(entries)
        keys = list(result.keys())
        assert keys == sorted(keys)
