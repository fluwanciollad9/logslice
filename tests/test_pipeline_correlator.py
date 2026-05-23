"""Integration tests for the correlator inside the pipeline."""
from datetime import datetime, timezone
from typing import List

from logslice.correlator import CorrelateOptions, correlate_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(
    msg: str = "boom",
    severity: str = "ERROR",
    second: int = 0,
) -> LogEntry:
    ts = datetime(2024, 6, 1, 12, 0, second, tzinfo=timezone.utc)
    return LogEntry(
        timestamp=ts,
        severity=severity,
        message=msg,
        source="svc",
        raw=msg,
        tags={},
    )


def _run(
    entries: List[LogEntry],
    min_severity: str = "ERROR",
    key: str = "ERROR",
    window: float = 60.0,
    min_matches: int = 2,
):
    filter_opts = FilterOptions(min_severity=min_severity)
    filtered = list(filter_entries(entries, filter_opts))
    corr_opts = CorrelateOptions(
        field="severity",
        key=key,
        window_seconds=window,
        min_matches=min_matches,
    )
    return list(correlate_entries(filtered, corr_opts))


class TestPipelineCorrelator:
    def test_only_filtered_entries_correlated(self):
        entries = [
            _entry(severity="INFO", second=0),
            _entry(severity="ERROR", second=1),
            _entry(severity="ERROR", second=2),
        ]
        groups = _run(entries)
        assert len(groups) == 1
        assert all(e.severity == "ERROR" for e in groups[0])

    def test_no_errors_after_filter_yields_no_groups(self):
        entries = [_entry(severity="INFO", second=i) for i in range(5)]
        groups = _run(entries, min_severity="ERROR")
        assert groups == []

    def test_group_size_matches_correlated_count(self):
        entries = [_entry(severity="ERROR", second=i) for i in range(4)]
        groups = _run(entries, min_matches=2)
        total = sum(len(g) for g in groups)
        assert total == 4
