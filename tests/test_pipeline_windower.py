"""Integration tests: windower wired into the pipeline via filter + slicer."""
from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from typing import List

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.windower import WindowOptions, window_entries, Window


def _entry(second: int, severity: str = "ERROR", msg: str = "boom") -> LogEntry:
    ts = datetime(2024, 6, 1, 12, 0, second, tzinfo=timezone.utc)
    return LogEntry(timestamp=ts, severity=severity, message=msg, raw=msg)


def _run(
    entries: list,
    severity: str | None = None,
    width: int = 60,
    step: int | None = None,
    min_entries: int = 1,
) -> List[Window]:
    fopts = FilterOptions(min_severity=severity)
    filtered = list(filter_entries(entries, fopts))
    wopts = WindowOptions(
        width_seconds=width,
        step_seconds=step,
        min_entries=min_entries,
    )
    return list(window_entries(filtered, wopts))


class TestPipelineWindower:
    def test_only_filtered_entries_windowed(self) -> None:
        entries = [
            _entry(0, "DEBUG", "noise"),
            _entry(5, "ERROR", "real"),
            _entry(10, "ERROR", "also real"),
        ]
        windows = _run(entries, severity="ERROR", width=60)
        assert len(windows) == 1
        assert windows[0].count == 2

    def test_no_entries_after_filter_yields_no_windows(self) -> None:
        entries = [_entry(0, "DEBUG"), _entry(10, "DEBUG")]
        windows = _run(entries, severity="ERROR", width=60)
        assert windows == []

    def test_min_entries_respected_after_filter(self) -> None:
        # Only one ERROR survives the filter; min_entries=2 should drop the window.
        entries = [
            _entry(0, "INFO"),
            _entry(5, "ERROR"),
            _entry(10, "INFO"),
        ]
        windows = _run(entries, severity="ERROR", width=60, min_entries=2)
        assert windows == []

    def test_window_count_property(self) -> None:
        entries = [_entry(i * 5, "ERROR") for i in range(6)]
        windows = _run(entries, severity="ERROR", width=60)
        assert windows[0].count == 6
