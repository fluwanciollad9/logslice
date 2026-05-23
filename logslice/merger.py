"""Merge multiple sorted log entry streams into a single ordered stream."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Tuple

from logslice.parser import LogEntry


@dataclass
class MergeOptions:
    """Options controlling how streams are merged."""

    key: str = "timestamp"  # 'timestamp' or 'severity'
    order: str = "asc"  # 'asc' or 'desc'
    tag_source: bool = False  # annotate each entry with its source index

    def __post_init__(self) -> None:
        if self.key not in ("timestamp", "severity"):
            raise ValueError(f"key must be 'timestamp' or 'severity', got {self.key!r}")
        if self.order not in ("asc", "desc"):
            raise ValueError(f"order must be 'asc' or 'desc', got {self.order!r}")


_SEVERITY_RANK = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}


def _entry_sort_key(entry: LogEntry, key: str) -> object:
    if key == "timestamp":
        return entry.timestamp or ""
    return _SEVERITY_RANK.get((entry.severity or "").upper(), -1)


def merge_entries(
    streams: List[Iterable[LogEntry]],
    options: MergeOptions | None = None,
) -> Iterator[LogEntry]:
    """Merge *streams* into one ordered stream.

    Each input stream is assumed to be individually sorted by *options.key*.
    A heap-based k-way merge is used so only one entry per stream is held in
    memory at a time.
    """
    if options is None:
        options = MergeOptions()

    reverse = options.order == "desc"

    # heap items: (sort_key, stream_index, tie_break, entry)
    heap: List[Tuple] = []
    iters = [iter(s) for s in streams]

    for idx, it in enumerate(iters):
        try:
            entry = next(it)
            raw_key = _entry_sort_key(entry, options.key)
            heap.append((raw_key, idx, 0, entry))
        except StopIteration:
            pass

    heapq.heapify(heap)
    counter = 0

    while heap:
        raw_key, idx, _, entry = heapq.heappop(heap)

        if options.tag_source:
            tags = dict(entry.tags) if entry.tags else {}
            tags["_source"] = str(idx)
            entry = LogEntry(
                timestamp=entry.timestamp,
                severity=entry.severity,
                message=entry.message,
                raw=entry.raw,
                tags=tags,
            )

        yield entry
        counter += 1

        try:
            nxt = next(iters[idx])
            nk = _entry_sort_key(nxt, options.key)
            heapq.heappush(heap, (nk, idx, counter, nxt))
        except StopIteration:
            pass
