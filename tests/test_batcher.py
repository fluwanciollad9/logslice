"""Tests for logslice.batcher."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.batcher import Batch, BatchOptions, batch_entries
from logslice.parser import LogEntry


def _entry(msg: str = "hello", ts: datetime | None = None) -> LogEntry:
    return LogEntry(
        timestamp=ts,
        severity="INFO",
        message=msg,
        raw=msg,
    )


def _ts(seconds: float) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


# ---------------------------------------------------------------------------
# BatchOptions validation
# ---------------------------------------------------------------------------

class TestBatchOptions:
    def test_defaults(self):
        opts = BatchOptions()
        assert opts.size == 100
        assert opts.window_seconds == 0.0

    def test_zero_size_raises(self):
        with pytest.raises(ValueError, match="size"):
            BatchOptions(size=0)

    def test_negative_size_raises(self):
        with pytest.raises(ValueError, match="size"):
            BatchOptions(size=-1)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            BatchOptions(window_seconds=-1.0)


# ---------------------------------------------------------------------------
# batch_entries — size-based
# ---------------------------------------------------------------------------

class TestBatchEntriesBySize:
    def test_empty_input_yields_nothing(self):
        result = list(batch_entries([], BatchOptions(size=5)))
        assert result == []

    def test_single_batch_when_fewer_than_size(self):
        entries = [_entry(str(i)) for i in range(3)]
        batches = list(batch_entries(entries, BatchOptions(size=10)))
        assert len(batches) == 1
        assert batches[0].count == 3

    def test_exact_multiple_yields_correct_batches(self):
        entries = [_entry(str(i)) for i in range(6)]
        batches = list(batch_entries(entries, BatchOptions(size=2)))
        assert len(batches) == 3
        assert all(b.count == 2 for b in batches)

    def test_remainder_forms_final_batch(self):
        entries = [_entry(str(i)) for i in range(7)]
        batches = list(batch_entries(entries, BatchOptions(size=3)))
        assert len(batches) == 3
        assert batches[-1].count == 1

    def test_default_options_used_when_none(self):
        entries = [_entry(str(i)) for i in range(5)]
        batches = list(batch_entries(entries))
        assert len(batches) == 1
        assert batches[0].count == 5


# ---------------------------------------------------------------------------
# batch_entries — window-based
# ---------------------------------------------------------------------------

class TestBatchEntriesByWindow:
    def test_window_splits_on_time_gap(self):
        entries = [
            _entry("a", _ts(0)),
            _entry("b", _ts(1)),
            _entry("c", _ts(10)),  # gap > 5 s window
            _entry("d", _ts(11)),
        ]
        batches = list(batch_entries(entries, BatchOptions(size=100, window_seconds=5)))
        assert len(batches) == 2
        assert batches[0].count == 2
        assert batches[1].count == 2

    def test_no_split_when_within_window(self):
        entries = [_entry(str(i), _ts(i)) for i in range(4)]
        batches = list(batch_entries(entries, BatchOptions(size=100, window_seconds=10)))
        assert len(batches) == 1

    def test_entries_without_timestamps_not_window_split(self):
        entries = [_entry(str(i)) for i in range(5)]
        batches = list(batch_entries(entries, BatchOptions(size=100, window_seconds=1)))
        assert len(batches) == 1
