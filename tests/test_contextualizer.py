"""Tests for logslice.contextualizer."""
import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.contextualizer import ContextOptions, contextualize_entries, sliding_context


def _entry(msg: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=msg,
        raw=f"2024-01-01T00:00:00Z {severity} {msg}",
    )


ENTRIES = [_entry(f"line {i}") for i in range(6)]  # indices 0-5


class TestContextOptions:
    def test_defaults(self):
        opts = ContextOptions()
        assert opts.before == 0
        assert opts.after == 0

    def test_negative_before_raises(self):
        with pytest.raises(ValueError, match="before"):
            ContextOptions(before=-1)

    def test_negative_after_raises(self):
        with pytest.raises(ValueError, match="after"):
            ContextOptions(after=-1)


class TestContextualizeEntries:
    def test_empty_entries_yields_nothing(self):
        result = list(contextualize_entries([], matched=set()))
        assert result == []

    def test_no_matches_yields_nothing(self):
        result = list(contextualize_entries(ENTRIES, matched=set()))
        assert result == []

    def test_match_only_no_context(self):
        result = list(contextualize_entries(ENTRIES, matched={2}))
        assert result == [ENTRIES[2]]

    def test_before_context(self):
        opts = ContextOptions(before=2)
        result = list(contextualize_entries(ENTRIES, matched={3}, options=opts))
        assert result == ENTRIES[1:4]

    def test_after_context(self):
        opts = ContextOptions(after=2)
        result = list(contextualize_entries(ENTRIES, matched={1}, options=opts))
        assert result == ENTRIES[1:4]

    def test_before_and_after_context(self):
        opts = ContextOptions(before=1, after=1)
        result = list(contextualize_entries(ENTRIES, matched={3}, options=opts))
        assert result == ENTRIES[2:5]

    def test_context_clamped_at_boundaries(self):
        opts = ContextOptions(before=5, after=5)
        result = list(contextualize_entries(ENTRIES, matched={0}, options=opts))
        assert result == ENTRIES  # all entries

    def test_overlapping_windows_deduped(self):
        opts = ContextOptions(after=2)
        result = list(contextualize_entries(ENTRIES, matched={0, 1}, options=opts))
        assert result == ENTRIES[0:4]
        assert len(result) == len(set(id(e) for e in result))


class TestSlidingContext:
    def _is_error(self, entry: LogEntry) -> bool:
        return entry.severity == "ERROR"

    def test_no_matches_yields_nothing(self):
        result = list(sliding_context(ENTRIES, lambda e: False))
        assert result == []

    def test_match_only_no_context(self):
        entries = [_entry("ok"), _entry("bad", "ERROR"), _entry("ok")]
        result = list(sliding_context(entries, self._is_error))
        assert result == [entries[1]]

    def test_before_lines_included(self):
        entries = [_entry("a"), _entry("b"), _entry("bad", "ERROR")]
        opts = ContextOptions(before=1)
        result = list(sliding_context(entries, self._is_error, opts))
        assert result == [entries[1], entries[2]]

    def test_after_lines_included(self):
        entries = [_entry("bad", "ERROR"), _entry("a"), _entry("b")]
        opts = ContextOptions(after=2)
        result = list(sliding_context(entries, self._is_error, opts))
        assert result == entries

    def test_no_duplicate_entries_in_overlapping_windows(self):
        entries = [_entry("bad", "ERROR"), _entry("x"), _entry("bad", "ERROR")]
        opts = ContextOptions(after=1)
        result = list(sliding_context(entries, self._is_error, opts))
        # entries[1] is after-context of [0] and before [2]; should appear once
        assert result.count(entries[1]) == 1
