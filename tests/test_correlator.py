"""Tests for logslice.correlator."""
from datetime import datetime, timezone
from typing import Optional

import pytest

from logslice.correlator import CorrelateOptions, correlate_entries
from logslice.parser import LogEntry


def _entry(
    msg: str = "hello",
    severity: str = "INFO",
    ts: Optional[datetime] = None,
    source: str = "app",
    tags: Optional[dict] = None,
) -> LogEntry:
    return LogEntry(
        timestamp=ts,
        severity=severity,
        message=msg,
        source=source,
        raw=msg,
        tags=tags or {},
    )


def _ts(second: int) -> datetime:
    return datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc)


class TestCorrelateOptions:
    def test_defaults(self):
        opts = CorrelateOptions(key="mykey")
        assert opts.field == "tag"
        assert opts.window_seconds == 60.0
        assert opts.min_matches == 2

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="field must be one of"):
            CorrelateOptions(field="unknown", key="x")

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key must be"):
            CorrelateOptions(key="")

    def test_non_positive_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            CorrelateOptions(key="x", window_seconds=0)

    def test_min_matches_below_one_raises(self):
        with pytest.raises(ValueError, match="min_matches must be at least 1"):
            CorrelateOptions(key="x", min_matches=0)


class TestCorrelateEntries:
    def test_no_matching_entries_yields_nothing(self):
        entries = [_entry(severity="INFO")]
        opts = CorrelateOptions(field="severity", key="ERROR")
        assert list(correlate_entries(entries, opts)) == []

    def test_single_match_below_min_not_emitted(self):
        entries = [_entry(severity="ERROR", ts=_ts(0))]
        opts = CorrelateOptions(field="severity", key="ERROR", min_matches=2)
        assert list(correlate_entries(entries, opts)) == []

    def test_two_matches_within_window_emitted(self):
        entries = [
            _entry(severity="ERROR", ts=_ts(0)),
            _entry(severity="ERROR", ts=_ts(10)),
        ]
        opts = CorrelateOptions(field="severity", key="ERROR", window_seconds=60)
        groups = list(correlate_entries(entries, opts))
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_entries_outside_window_split_into_groups(self):
        entries = [
            _entry(severity="ERROR", ts=_ts(0)),
            _entry(severity="ERROR", ts=_ts(5)),
            _entry(severity="ERROR", ts=_ts(120)),
            _entry(severity="ERROR", ts=_ts(125)),
        ]
        opts = CorrelateOptions(field="severity", key="ERROR", window_seconds=60)
        groups = list(correlate_entries(entries, opts))
        assert len(groups) == 2

    def test_non_matching_entries_ignored(self):
        entries = [
            _entry(severity="INFO", ts=_ts(0)),
            _entry(severity="ERROR", ts=_ts(1)),
            _entry(severity="ERROR", ts=_ts(2)),
        ]
        opts = CorrelateOptions(field="severity", key="ERROR", min_matches=2)
        groups = list(correlate_entries(entries, opts))
        assert len(groups) == 1
        assert all(e.severity == "ERROR" for e in groups[0])

    def test_min_matches_one_emits_individual_groups(self):
        entries = [_entry(severity="ERROR", ts=_ts(i)) for i in range(3)]
        opts = CorrelateOptions(field="severity", key="ERROR", min_matches=1)
        groups = list(correlate_entries(entries, opts))
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_entries_without_timestamp_appended_to_bucket(self):
        entries = [
            _entry(severity="ERROR", ts=_ts(0)),
            _entry(severity="ERROR", ts=None),
        ]
        opts = CorrelateOptions(field="severity", key="ERROR", min_matches=2)
        groups = list(correlate_entries(entries, opts))
        assert len(groups) == 1
        assert len(groups[0]) == 2
