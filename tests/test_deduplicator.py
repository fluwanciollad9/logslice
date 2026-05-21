"""Tests for logslice.deduplicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.deduplicator import DedupeOptions, deduplicate_entries, duplicate_counts
from logslice.parser import LogEntry


def _entry(message: str, severity: str = "INFO", ts: str = "2024-01-01T00:00:00") -> LogEntry:
    return LogEntry(
        timestamp=datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=f"{ts} {severity} {message}",
    )


class TestDedupeOptions:
    def test_defaults(self):
        opts = DedupeOptions()
        assert opts.enabled is False
        assert opts.message_only is True
        assert opts.max_cache == 10_000

    def test_invalid_max_cache_raises(self):
        with pytest.raises(ValueError, match="max_cache"):
            DedupeOptions(max_cache=0)


class TestDeduplicateEntries:
    def test_passthrough_when_disabled(self):
        entries = [_entry("hello"), _entry("hello"), _entry("world")]
        result = list(deduplicate_entries(entries, DedupeOptions(enabled=False)))
        assert len(result) == 3

    def test_passthrough_when_no_options(self):
        entries = [_entry("hello"), _entry("hello")]
        result = list(deduplicate_entries(entries))
        assert len(result) == 2

    def test_removes_duplicate_messages(self):
        entries = [_entry("same"), _entry("same"), _entry("different")]
        result = list(deduplicate_entries(entries, DedupeOptions(enabled=True)))
        assert len(result) == 2
        assert result[0].message == "same"
        assert result[1].message == "different"

    def test_different_severity_not_deduplicated(self):
        entries = [_entry("msg", severity="INFO"), _entry("msg", severity="ERROR")]
        result = list(deduplicate_entries(entries, DedupeOptions(enabled=True)))
        assert len(result) == 2

    def test_same_message_different_timestamp_deduped_when_message_only(self):
        entries = [
            _entry("msg", ts="2024-01-01T00:00:00"),
            _entry("msg", ts="2024-01-01T01:00:00"),
        ]
        opts = DedupeOptions(enabled=True, message_only=True)
        result = list(deduplicate_entries(entries, opts))
        assert len(result) == 1

    def test_same_message_different_timestamp_kept_when_not_message_only(self):
        entries = [
            _entry("msg", ts="2024-01-01T00:00:00"),
            _entry("msg", ts="2024-01-01T01:00:00"),
        ]
        opts = DedupeOptions(enabled=True, message_only=False)
        result = list(deduplicate_entries(entries, opts))
        assert len(result) == 2

    def test_cache_eviction_does_not_crash(self):
        opts = DedupeOptions(enabled=True, max_cache=3)
        entries = [_entry(f"msg-{i}") for i in range(10)]
        result = list(deduplicate_entries(entries, opts))
        assert len(result) == 10


class TestDuplicateCounts:
    def test_counts_occurrences(self):
        entries = [_entry("a"), _entry("a"), _entry("b")]
        counts = duplicate_counts(entries)
        assert sum(counts.values()) == 3
        assert len(counts) == 2

    def test_unique_entries_all_count_one(self):
        entries = [_entry("x"), _entry("y"), _entry("z")]
        counts = duplicate_counts(entries)
        assert all(v == 1 for v in counts.values())
