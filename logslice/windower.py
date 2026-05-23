"""Sliding time-window grouping of log entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Generator, Iterable, List

from logslice.parser import LogEntry


@dataclass
class WindowOptions:
    """Configuration for time-window grouping."""

    width_seconds: int = 60
    step_seconds: int | None = None  # defaults to width_seconds (tumbling)
    min_entries: int = 1

    def __post_init__(self) -> None:
        if self.width_seconds <= 0:
            raise ValueError("width_seconds must be > 0")
        if self.step_seconds is None:
            self.step_seconds = self.width_seconds
        if self.step_seconds <= 0:
            raise ValueError("step_seconds must be > 0")
        if self.min_entries < 1:
            raise ValueError("min_entries must be >= 1")


@dataclass
class Window:
    """A single time window containing matched entries."""

    start: datetime
    end: datetime
    entries: List[LogEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)


def window_entries(
    entries: Iterable[LogEntry],
    opts: WindowOptions | None = None,
) -> Generator[Window, None, None]:
    """Group entries into time windows.

    Entries without a timestamp are silently skipped.
    Only windows that contain at least *min_entries* entries are yielded.
    """
    if opts is None:
        opts = WindowOptions()

    width = timedelta(seconds=opts.width_seconds)
    step = timedelta(seconds=opts.step_seconds)  # type: ignore[arg-type]

    # Materialise only entries that carry a timestamp.
    timed: List[LogEntry] = [
        e for e in entries if e.timestamp is not None
    ]
    if not timed:
        return

    window_start: datetime = timed[0].timestamp  # type: ignore[assignment]
    last_ts: datetime = timed[-1].timestamp  # type: ignore[assignment]

    while window_start <= last_ts:
        window_end = window_start + width
        bucket = Window(start=window_start, end=window_end)
        for entry in timed:
            ts: datetime = entry.timestamp  # type: ignore[assignment]
            if window_start <= ts < window_end:
                bucket.entries.append(entry)
        if bucket.count >= opts.min_entries:
            yield bucket
        window_start += step
