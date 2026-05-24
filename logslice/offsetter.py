"""Timestamp offsetting: shift entry timestamps by a fixed delta."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class OffsetOptions:
    """Options for timestamp offsetting.

    Attributes:
        seconds: Number of seconds to shift timestamps (may be negative).
        skip_unparsed: When True, entries without a timestamp pass through
                       unchanged; when False they are dropped.
    """

    seconds: float = 0.0
    skip_unparsed: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, (int, float)):
            raise TypeError("seconds must be a number")


def _shift(entry: LogEntry, delta: timedelta) -> LogEntry:
    """Return a new LogEntry with its timestamp shifted by *delta*."""
    if entry.timestamp is None:
        return entry
    new_ts = entry.timestamp + delta
    return LogEntry(
        timestamp=new_ts,
        severity=entry.severity,
        message=entry.message,
        raw=entry.raw,
        tags=dict(entry.tags) if entry.tags else {},
    )


def offset_entries(
    entries: Iterable[LogEntry],
    opts: OffsetOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries with timestamps shifted by *opts.seconds*.

    Entries that have no timestamp are either passed through unchanged
    (``skip_unparsed=True``) or dropped (``skip_unparsed=False``).
    """
    if opts is None:
        opts = OffsetOptions()

    delta = timedelta(seconds=opts.seconds)

    for entry in entries:
        if entry.timestamp is None:
            if opts.skip_unparsed:
                yield entry
            # else: drop silently
        else:
            yield _shift(entry, delta)
