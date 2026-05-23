"""Tests for logslice.limiter."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.limiter import LimitOptions, limit_entries


def _entry(msg: str) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity="INFO",
        message=msg,
        raw=msg,
    )


def _entries(n: int) -> list[LogEntry]:
    return [_entry(f"msg-{i}") for i in range(n)]


# ---------------------------------------------------------------------------
# LimitOptions validation
# ---------------------------------------------------------------------------

class TestLimitOptions:
    def test_defaults(self):
        opts = LimitOptions()
        assert opts.head is None
        assert opts.tail is None

    def test_negative_head_raises(self):
        with pytest.raises(ValueError, match="head"):
            LimitOptions(head=-1)

    def test_negative_tail_raises(self):
        with pytest.raises(ValueError, match="tail"):
            LimitOptions(tail=-1)

    def test_head_and_tail_together_raises(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            LimitOptions(head=5, tail=5)

    def test_zero_head_valid(self):
        opts = LimitOptions(head=0)
        assert opts.head == 0

    def test_zero_tail_valid(self):
        opts = LimitOptions(tail=0)
        assert opts.tail == 0


# ---------------------------------------------------------------------------
# limit_entries behaviour
# ---------------------------------------------------------------------------

class TestLimitEntries:
    def test_no_opts_yields_all(self):
        entries = _entries(5)
        result = list(limit_entries(entries))
        assert len(result) == 5

    def test_none_opts_yields_all(self):
        entries = _entries(5)
        result = list(limit_entries(entries, None))
        assert len(result) == 5

    def test_head_limits_to_n(self):
        result = list(limit_entries(_entries(10), LimitOptions(head=3)))
        assert len(result) == 3
        assert result[0].message == "msg-0"
        assert result[-1].message == "msg-2"

    def test_head_larger_than_stream(self):
        result = list(limit_entries(_entries(3), LimitOptions(head=10)))
        assert len(result) == 3

    def test_head_zero_yields_nothing(self):
        result = list(limit_entries(_entries(5), LimitOptions(head=0)))
        assert result == []

    def test_tail_keeps_last_n(self):
        result = list(limit_entries(_entries(10), LimitOptions(tail=3)))
        assert len(result) == 3
        assert result[0].message == "msg-7"
        assert result[-1].message == "msg-9"

    def test_tail_larger_than_stream(self):
        result = list(limit_entries(_entries(3), LimitOptions(tail=10)))
        assert len(result) == 3

    def test_tail_zero_yields_nothing(self):
        result = list(limit_entries(_entries(5), LimitOptions(tail=0)))
        assert result == []

    def test_head_preserves_entry_fields(self):
        entries = _entries(5)
        result = list(limit_entries(entries, LimitOptions(head=2)))
        assert result[0] is entries[0]
        assert result[1] is entries[1]
