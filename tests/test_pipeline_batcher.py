"""Integration tests: batcher wired after filter inside pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.batcher import BatchOptions, batch_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(
    msg: str = "msg",
    severity: str = "INFO",
    ts: datetime | None = None,
) -> LogEntry:
    return LogEntry(
        timestamp=ts,
        severity=severity,
        message=msg,
        raw=msg,
    )


def _ts(s: float) -> datetime:
    return datetime.fromtimestamp(s, tz=timezone.utc)


def _run(
    entries,
    filter_opts: FilterOptions | None = None,
    batch_opts: BatchOptions | None = None,
):
    filtered = filter_entries(entries, filter_opts or FilterOptions())
    return list(batch_entries(filtered, batch_opts or BatchOptions()))


class TestPipelineBatcher:
    def test_only_filtered_entries_batched(self):
        entries = [
            _entry("a", "ERROR"),
            _entry("b", "INFO"),
            _entry("c", "ERROR"),
        ]
        batches = _run(
            entries,
            FilterOptions(min_severity="ERROR"),
            BatchOptions(size=10),
        )
        assert sum(b.count for b in batches) == 2

    def test_batch_count_matches_size(self):
        entries = [_entry(str(i), "WARNING") for i in range(9)]
        batches = _run(
            entries,
            FilterOptions(min_severity="WARNING"),
            BatchOptions(size=4),
        )
        assert len(batches) == 3  # 4 + 4 + 1

    def test_empty_after_filter_yields_no_batches(self):
        entries = [_entry("x", "DEBUG")]
        batches = _run(
            entries,
            FilterOptions(min_severity="ERROR"),
            BatchOptions(size=5),
        )
        assert batches == []
