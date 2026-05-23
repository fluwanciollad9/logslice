"""Throttle log entries by emitting at most N entries per time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ThrottleOptions:
    """Configuration for the throttle stage."""

    max_per_window: int = 0          # 0 means disabled
    window_seconds: float = 1.0      # rolling window width in seconds
    by_severity: bool = False        # apply limit independently per severity

    def __post_init__(self) -> None:
        if self.max_per_window < 0:
            raise ValueError("max_per_window must be >= 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")


@dataclass
 class _Counter:
    """Sliding-window counter for a single key."""

    timestamps: list[datetime] = field(default_factory=list)

    def admit(self, ts: datetime, window: timedelta, limit: int) -> bool:
        """Return True if the entry should be emitted."""
        cutoff = ts - window
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        if len(self.timestamps) < limit:
            self.timestamps.append(ts)
            return True
        return False


def throttle_entries(
    entries: Iterable[LogEntry],
    opts: ThrottleOptions,
) -> Iterator[LogEntry]:
    """Yield entries that fall within the allowed rate.

    Entries without a timestamp are always emitted.
    """
    if opts.max_per_window == 0:
        yield from entries
        return

    window = timedelta(seconds=opts.window_seconds)
    counters: dict[str, _Counter] = {}

    for entry in entries:
        if entry.timestamp is None:
            yield entry
            continue

        key = entry.severity if opts.by_severity else "__global__"
        if key not in counters:
            counters[key] = _Counter()

        if counters[key].admit(entry.timestamp, window, opts.max_per_window):
            yield entry
