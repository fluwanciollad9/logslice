"""Integration tests: joiner wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.joiner import JoinOptions, join_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=message,
    )


def _run(entries, join_opts=None, filter_opts=None):
    """Filter then join, mirroring typical pipeline ordering."""
    filtered = filter_entries(entries, filter_opts or FilterOptions())
    joined = join_entries(filtered, join_opts or JoinOptions())
    return list(joined)


class TestPipelineJoiner:
    def test_join_disabled_by_default_passes_all(self):
        entries = [_entry("a"), _entry("b"), _entry("c")]
        result = _run(entries)
        assert len(result) == 3

    def test_only_filtered_entries_are_joined(self):
        entries = [
            _entry("error head", severity="ERROR"),
            _entry("  error cont", severity="ERROR"),
            _entry("info line", severity="INFO"),
        ]
        result = _run(
            entries,
            filter_opts=FilterOptions(min_severity="ERROR"),
        )
        # INFO line excluded before joining
        assert len(result) == 1
        assert "error cont" in result[0].message

    def test_join_merges_continuation_after_filter(self):
        entries = [
            _entry("start"),
            _entry("  part two"),
            _entry("  part three"),
        ]
        result = _run(entries, join_opts=JoinOptions(separator=" | "))
        assert len(result) == 1
        assert result[0].message == "start | part two | part three"

    def test_separate_groups_survive_pipeline(self):
        entries = [
            _entry("first"),
            _entry("  first-cont"),
            _entry("second"),
            _entry("  second-cont"),
        ]
        result = _run(entries)
        assert len(result) == 2
