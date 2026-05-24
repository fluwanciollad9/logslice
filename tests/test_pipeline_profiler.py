"""Integration tests: profiler wired into the pipeline."""
from __future__ import annotations

from datetime import datetime

from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry
from logslice.profiler import ProfileOptions, profile_entries


def _entry(
    severity: str = "INFO",
    ts: datetime | None = None,
    message: str = "msg",
) -> LogEntry:
    return LogEntry(
        raw=f"{severity} {message}",
        timestamp=ts or datetime(2024, 6, 1, 12, 0, 0),
        severity=severity,
        message=message,
    )


def _run(
    entries: list[LogEntry],
    min_severity: str = "DEBUG",
    bucket_seconds: int = 60,
) -> tuple[list[LogEntry], object]:
    filtered = filter_entries(iter(entries), FilterOptions(min_severity=min_severity))
    it, result = profile_entries(filtered, ProfileOptions(bucket_seconds=bucket_seconds))
    return list(it), result


class TestPipelineProfiler:
    def test_only_filtered_entries_profiled(self) -> None:
        entries = [
            _entry("DEBUG"),
            _entry("INFO"),
            _entry("ERROR"),
        ]
        out, result = _run(entries, min_severity="INFO")
        assert result.total == 2
        assert "DEBUG" not in result.severity_counts

    def test_profile_counts_match_output_length(self) -> None:
        entries = [_entry("ERROR")] * 5
        out, result = _run(entries)
        assert len(out) == result.total == 5

    def test_severity_distribution_after_filter(self) -> None:
        entries = [_entry("ERROR")] * 2 + [_entry("WARNING")] * 3
        out, result = _run(entries, min_severity="WARNING")
        assert result.severity_counts.get("ERROR", 0) == 2
        assert result.severity_counts.get("WARNING", 0) == 3
