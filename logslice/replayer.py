"""Replayer: re-emit log entries with timing delays that mirror original timestamps."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ReplayOptions:
    speed: float = 1.0          # multiplier; 2.0 = twice as fast
    real_time: bool = True      # if False, yield immediately (dry-run)
    max_delay: float = 5.0      # cap any single inter-event gap (seconds)

    def __post_init__(self) -> None:
        if self.speed <= 0:
            raise ValueError("speed must be positive")
        if self.max_delay < 0:
            raise ValueError("max_delay must be >= 0")


def replay_entries(
    entries: Iterable[LogEntry],
    options: ReplayOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries, sleeping between them to honour original timing."""
    opts = options or ReplayOptions()
    prev_ts: float | None = None

    for entry in entries:
        if opts.real_time and entry.timestamp is not None:
            current_ts = entry.timestamp.timestamp()
            if prev_ts is not None:
                gap = (current_ts - prev_ts) / opts.speed
                gap = min(gap, opts.max_delay)
                if gap > 0:
                    time.sleep(gap)
            prev_ts = current_ts

        yield entry
