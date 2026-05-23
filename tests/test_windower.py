"""Tests for logslice.windower."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from logslice.parser import LogEntry
from logslice.windower import Window, WindowOptions, window_entries


def _entry(ts: datetime | None, msg: str = "msg") -> LogEntry:
    return LogEntry(timestamp=ts, severity="INFO", message=msg, raw=msg)


def _ts(second: int) -> datetime:
    return datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# WindowOptions validation
# ---------------------------------------------------------------------------

class TestWindowOptions:
    def test_defaults(self) -> None:
        o = WindowOptions()
        assert o.width_seconds == 60
        assert o.step_seconds == 60
        assert o.min_entries == 1

    def test_step_defaults_to_width(self) -> None:
        o = WindowOptions(width_seconds=30)
        assert o.step_seconds == 30

    def test_explicit_step(self) -> None:
        o = WindowOptions(width_seconds=60, step_seconds=10)
        assert o.step_seconds == 10

    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width_seconds"):
            WindowOptions(width_seconds=0)

    def test_zero_step_raises(self) -> None:
        with pytest.raises(ValueError, match="step_seconds"):
            WindowOptions(step_seconds=0)

    def test_zero_min_entries_raises(self) -> None:
        with pytest.raises(ValueError, match="min_entries"):
            WindowOptions(min_entries=0)


# ---------------------------------------------------------------------------
# window_entries
# ---------------------------------------------------------------------------

class TestWindowEntries:
    def _run(self, entries: list, **kw) -> List[Window]:
        return list(window_entries(entries, WindowOptions(**kw)))

    def test_empty_input_yields_nothing(self) -> None:
        assert self._run([]) == []

    def test_entries_without_timestamp_are_skipped(self) -> None:
        result = self._run([_entry(None), _entry(None)], width_seconds=60)
        assert result == []

    def test_single_window_contains_all_entries(self) -> None:
        entries = [_entry(_ts(0)), _entry(_ts(10)), _entry(_ts(20))]
        windows = self._run(entries, width_seconds=60)
        assert len(windows) == 1
        assert windows[0].count == 3

    def test_tumbling_windows_no_overlap(self) -> None:
        entries = [_entry(_ts(0)), _entry(_ts(30)), _entry(_ts(60)), _entry(_ts(90))]
        windows = self._run(entries, width_seconds=30, step_seconds=30)
        counts = [w.count for w in windows]
        # Each 30-second tumbling window should hold exactly one entry.
        assert all(c == 1 for c in counts)
        assert len(windows) == 4

    def test_sliding_window_overlap(self) -> None:
        # entry at t=0 and t=10 both fall inside a 20s window starting at t=0
        # and also the window starting at t=5 (step=5).
        entries = [_entry(_ts(0)), _entry(_ts(10))]
        windows = self._run(entries, width_seconds=20, step_seconds=5)
        # At least one window should contain both entries.
        assert any(w.count == 2 for w in windows)

    def test_min_entries_filters_sparse_windows(self) -> None:
        entries = [_entry(_ts(0)), _entry(_ts(60))]
        windows = self._run(entries, width_seconds=30, step_seconds=30, min_entries=2)
        # No 30-second window contains 2 entries.
        assert windows == []

    def test_window_start_and_end_set_correctly(self) -> None:
        entries = [_entry(_ts(0))]
        windows = self._run(entries, width_seconds=30)
        assert windows[0].start == _ts(0)
        assert windows[0].end == _ts(30)

    def test_no_options_uses_defaults(self) -> None:
        entries = [_entry(_ts(0))]
        result = list(window_entries(entries))
        assert len(result) == 1
