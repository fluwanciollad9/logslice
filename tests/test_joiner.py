"""Tests for logslice.joiner."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.joiner import JoinOptions, join_entries
from logslice.parser import LogEntry


def _entry(message: str, ts: datetime | None = None) -> LogEntry:
    return LogEntry(
        timestamp=ts or datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity="INFO",
        message=message,
        raw=message,
    )


# ---------------------------------------------------------------------------
# JoinOptions validation
# ---------------------------------------------------------------------------

class TestJoinOptions:
    def test_defaults(self):
        opts = JoinOptions()
        assert opts.separator == " "
        assert opts.max_lines == 50

    def test_empty_pattern_raises(self):
        with pytest.raises(ValueError, match="continuation_pattern"):
            JoinOptions(continuation_pattern="")

    def test_invalid_regex_raises(self):
        with pytest.raises(Exception):
            JoinOptions(continuation_pattern="[invalid")

    def test_zero_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            JoinOptions(max_lines=0)

    def test_negative_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            JoinOptions(max_lines=-1)


# ---------------------------------------------------------------------------
# join_entries behaviour
# ---------------------------------------------------------------------------

class TestJoinEntries:
    def _run(self, entries, **kwargs):
        opts = JoinOptions(**kwargs) if kwargs else JoinOptions()
        return list(join_entries(entries, opts))

    def test_single_entry_passed_through(self):
        result = self._run([_entry("hello")])
        assert len(result) == 1
        assert result[0].message == "hello"

    def test_continuation_line_merged(self):
        entries = [_entry("first line"), _entry("  continuation")]
        result = self._run(entries)
        assert len(result) == 1
        assert result[0].message == "first line continuation"

    def test_non_continuation_not_merged(self):
        entries = [_entry("first"), _entry("second")]
        result = self._run(entries)
        assert len(result) == 2

    def test_custom_separator(self):
        entries = [_entry("a"), _entry("  b")]
        result = self._run(entries, separator="|")
        assert result[0].message == "a|b"

    def test_max_lines_limits_absorption(self):
        entries = [_entry("start"), _entry("  c1"), _entry("  c2"), _entry("  c3")]
        result = self._run(entries, max_lines=2)
        # c1 and c2 absorbed; c3 starts a new entry
        assert len(result) == 2
        assert "c1" in result[0].message
        assert "c2" in result[0].message
        assert result[1].message == "c3"

    def test_none_values_skipped(self):
        result = self._run([None, _entry("ok"), None])
        assert len(result) == 1
        assert result[0].message == "ok"

    def test_timestamp_preserved_from_first_line(self):
        ts = datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone.utc)
        entries = [_entry("head", ts=ts), _entry("  tail")]
        result = self._run(entries)
        assert result[0].timestamp == ts

    def test_multiple_groups(self):
        entries = [
            _entry("group1"),
            _entry("  cont1"),
            _entry("group2"),
            _entry("  cont2"),
        ]
        result = self._run(entries)
        assert len(result) == 2
        assert "cont1" in result[0].message
        assert "cont2" in result[1].message

    def test_empty_input_yields_nothing(self):
        assert self._run([]) == []
