"""Tests for logslice.pruner."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.pruner import PruneOptions, prune_entries


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=f"2024-01-01T00:00:00Z {severity} {message}",
    )


# ---------------------------------------------------------------------------
# PruneOptions validation
# ---------------------------------------------------------------------------

class TestPruneOptions:
    def test_defaults(self):
        opts = PruneOptions()
        assert opts.patterns == []
        assert opts.ignore_case is True
        assert opts.invert is False

    def test_empty_pattern_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            PruneOptions(patterns=[""])

    def test_invalid_regex_raises(self):
        with pytest.raises(ValueError, match="invalid prune pattern"):
            PruneOptions(patterns=["[unclosed"])

    def test_valid_pattern_accepted(self):
        opts = PruneOptions(patterns=[r"\bERROR\b"])
        assert len(opts.patterns) == 1


# ---------------------------------------------------------------------------
# prune_entries — default (discard matching)
# ---------------------------------------------------------------------------

class TestPruneEntries:
    def test_no_options_passes_all(self):
        entries = [_entry("hello"), _entry("world")]
        assert list(prune_entries(entries)) == entries

    def test_empty_patterns_passes_all(self):
        opts = PruneOptions(patterns=[])
        entries = [_entry("hello"), _entry("world")]
        assert list(prune_entries(entries, opts)) == entries

    def test_matching_entry_is_discarded(self):
        opts = PruneOptions(patterns=["noise"])
        entries = [_entry("useful log"), _entry("noisy noise here"), _entry("also useful")]
        result = list(prune_entries(entries, opts))
        assert len(result) == 2
        assert all("noise" not in e.message for e in result)

    def test_non_matching_entry_is_kept(self):
        opts = PruneOptions(patterns=["drop"])
        entry = _entry("keep this")
        assert list(prune_entries([entry], opts)) == [entry]

    def test_case_insensitive_by_default(self):
        opts = PruneOptions(patterns=["DEBUG"])
        entries = [_entry("debug message"), _entry("INFO message")]
        result = list(prune_entries(entries, opts))
        assert len(result) == 1
        assert result[0].message == "INFO message"

    def test_case_sensitive_when_disabled(self):
        opts = PruneOptions(patterns=["DEBUG"], ignore_case=False)
        entries = [_entry("debug message"), _entry("DEBUG message")]
        result = list(prune_entries(entries, opts))
        # lowercase 'debug' should survive; uppercase 'DEBUG' is pruned
        assert len(result) == 1
        assert result[0].message == "debug message"

    def test_multiple_patterns_any_match_discards(self):
        opts = PruneOptions(patterns=["foo", "bar"])
        entries = [_entry("foo here"), _entry("bar here"), _entry("clean")]
        result = list(prune_entries(entries, opts))
        assert len(result) == 1
        assert result[0].message == "clean"

    def test_invert_keeps_only_matching(self):
        opts = PruneOptions(patterns=["important"], invert=True)
        entries = [_entry("important event"), _entry("boring log"), _entry("very important")]
        result = list(prune_entries(entries, opts))
        assert len(result) == 2
        assert all("important" in e.message for e in result)

    def test_invert_no_match_yields_nothing(self):
        opts = PruneOptions(patterns=["critical"], invert=True)
        entries = [_entry("info"), _entry("debug")]
        assert list(prune_entries(entries, opts)) == []
