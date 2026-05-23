"""Batch log entries into fixed-size or time-bounded groups."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable, Iterator, List

from logslice.parser import LogEntry


@dataclass
class BatchOptions:
    size: int = 100
    window_seconds: float = 0.0  # 0 means size-only batching

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError("size must be >= 1")
        if self.window_seconds < 0:
            raise ValueError("window_seconds must be >= 0")


@dataclass
class Batch:
    entries: List[LogEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)


def _flush(batch: Batch) -> Batch:
    """Return the current batch and start a fresh one."""
    return batch, Batch()


def batch_entries(
    entries: Iterable[LogEntry],
    options: BatchOptions | None = None,
) -> Iterator[Batch]:
    """Yield Batch objects according to *options*.

    A batch is emitted when either:
    - it reaches *options.size* entries, or
    - the timestamp gap between the first and latest entry exceeds
      *options.window_seconds* (when > 0).
    """
    if options is None:
        options = BatchOptions()

    window = (
        timedelta(seconds=options.window_seconds)
        if options.window_seconds > 0
        else None
    )

    current = Batch()
    batch_start_ts = None

    for entry in entries:
        if window is not None and entry.timestamp is not None:
            if batch_start_ts is None:
                batch_start_ts = entry.timestamp
            elif entry.timestamp - batch_start_ts >= window:
                if current.count:
                    yield current
                current = Batch()
                batch_start_ts = entry.timestamp

        current.append(entry)

        if current.count >= options.size:
            yield current
            current = Batch()
            batch_start_ts = None

    if current.count:
        yield current
