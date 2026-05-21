"""Tests for logslice.aggregator."""

from datetime import datetime, timezone
import pytest

from logslice.aggregator import AggregateOptions, Bucket, _bucket_key, aggregate_entries
from logslice.parser import LogEntry


def _entry(ts: datetime, severity: str = "INFO", msg: str = "test") -> LogEntry:
    return LogEntry(timestamp=ts, severity=severity, message=msg, raw=msg)


def _ts(second: int) -> datetime:
    return datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# AggregateOptions
# ---------------------------------------------------------------------------

class TestAggregateOptions:
    def test_default_bucket_is_60_seconds(self):
        opts = AggregateOptions()
        assert opts.bucket_seconds == 60

    def test_zero_bucket_raises(self):
        with pytest.raises(ValueError):
            AggregateOptions(bucket_seconds=0)

    def test_negative_bucket_raises(self):
        with pytest.raises(ValueError):
            AggregateOptions(bucket_seconds=-10)


# ---------------------------------------------------------------------------
# _bucket_key
# ---------------------------------------------------------------------------

def test_bucket_key_rounds_down():
    ts = datetime(2024, 1, 1, 0, 1, 45, tzinfo=timezone.utc)
    key = _bucket_key(ts, 60)
    assert key == datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)


def test_bucket_key_exact_boundary_unchanged():
    ts = datetime(2024, 1, 1, 0, 2, 0, tzinfo=timezone.utc)
    key = _bucket_key(ts, 60)
    assert key == ts


# ---------------------------------------------------------------------------
# aggregate_entries
# ---------------------------------------------------------------------------

def test_empty_input_returns_empty_list():
    assert aggregate_entries([]) == []


def test_entries_without_timestamp_are_skipped():
    entry = LogEntry(timestamp=None, severity="INFO", message="x", raw="x")
    result = aggregate_entries([entry])
    assert result == []


def test_single_entry_creates_one_bucket():
    result = aggregate_entries([_entry(_ts(10))], AggregateOptions(bucket_seconds=60))
    assert len(result) == 1
    assert result[0].count == 1


def test_entries_in_same_bucket_are_grouped():
    entries = [_entry(_ts(5)), _entry(_ts(30)), _entry(_ts(59))]
    result = aggregate_entries(entries, AggregateOptions(bucket_seconds=60))
    assert len(result) == 1
    assert result[0].count == 3


def test_entries_in_different_buckets_are_split():
    entries = [_entry(_ts(5)), _entry(_ts(65))]
    result = aggregate_entries(entries, AggregateOptions(bucket_seconds=60))
    assert len(result) == 2


def test_buckets_sorted_by_start_time():
    entries = [_entry(_ts(65)), _entry(_ts(5))]
    result = aggregate_entries(entries, AggregateOptions(bucket_seconds=60))
    assert result[0].start < result[1].start


def test_severity_breakdown_populated():
    entries = [_entry(_ts(5), "INFO"), _entry(_ts(10), "ERROR"), _entry(_ts(15), "INFO")]
    result = aggregate_entries(entries, AggregateOptions(bucket_seconds=60))
    assert result[0].by_severity["INFO"] == 2
    assert result[0].by_severity["ERROR"] == 1


def test_default_options_used_when_none_provided():
    result = aggregate_entries([_entry(_ts(5))])
    assert len(result) == 1
