"""Tests for logslice.scoper."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.scoper import ScopeOptions, scope_entries


def _entry(msg: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity="INFO",
        message=msg,
        raw=msg,
    )


def _entries(n: int) -> list[LogEntry]:
    return [_entry(f"line {i}") for i in range(n)]


# ---------------------------------------------------------------------------
# ScopeOptions validation
# ---------------------------------------------------------------------------

class TestScopeOptions:
    def test_defaults(self):
        opts = ScopeOptions()
        assert opts.start == 0
        assert opts.stop is None
        assert opts.step == 1

    def test_negative_start_raises(self):
        with pytest.raises(ValueError, match="start"):
            ScopeOptions(start=-1)

    def test_stop_less_than_start_raises(self):
        with pytest.raises(ValueError, match="stop"):
            ScopeOptions(start=5, stop=3)

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="step"):
            ScopeOptions(step=0)

    def test_negative_step_raises(self):
        with pytest.raises(ValueError, match="step"):
            ScopeOptions(step=-1)


# ---------------------------------------------------------------------------
# scope_entries behaviour
# ---------------------------------------------------------------------------

class TestScopeEntries:
    def test_none_options_yields_all(self):
        src = _entries(5)
        result = list(scope_entries(src, None))
        assert result == src

    def test_start_skips_leading_entries(self):
        src = _entries(5)
        result = list(scope_entries(src, ScopeOptions(start=2)))
        assert result == src[2:]

    def test_stop_limits_trailing_entries(self):
        src = _entries(5)
        result = list(scope_entries(src, ScopeOptions(stop=3)))
        assert result == src[:3]

    def test_start_and_stop_slice(self):
        src = _entries(10)
        result = list(scope_entries(src, ScopeOptions(start=2, stop=6)))
        assert result == src[2:6]

    def test_step_keeps_every_nth(self):
        src = _entries(6)
        result = list(scope_entries(src, ScopeOptions(step=2)))
        assert result == src[::2]

    def test_step_with_start(self):
        src = _entries(10)
        result = list(scope_entries(src, ScopeOptions(start=1, step=3)))
        assert [e.message for e in result] == ["line 1", "line 4", "line 7"]

    def test_empty_input_yields_nothing(self):
        result = list(scope_entries([], ScopeOptions(start=0, stop=5)))
        assert result == []

    def test_stop_equal_to_start_yields_nothing(self):
        src = _entries(5)
        result = list(scope_entries(src, ScopeOptions(start=2, stop=2)))
        assert result == []
