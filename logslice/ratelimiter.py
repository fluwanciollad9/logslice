"""Rate limiting for log output — suppress repeated entries within a time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterator

from logslice.parser import LogEntry


@dataclass
class RateLimitOptions:
    """Options controlling per-message rate limiting."""

    window_seconds: float = 60.0
    max_per_window: int = 5

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_per_window < 1:
            raise ValueError("max_per_window must be at least 1")


@dataclass
class _Bucket:
    count: int = 0
    window_start: datetime | None = None


def _fingerprint(entry: LogEntry) -> str:
    """Stable key that identifies 'the same' message regardless of timestamp."""
    return f"{entry.severity}:{entry.message}"


def ratelimit_entries(
    entries: Iterator[LogEntry],
    options: RateLimitOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries, suppressing those that exceed *max_per_window* within *window_seconds*.

    Entries without a timestamp are always passed through unchanged.
    """
    if options is None:
        yield from entries
        return

    window = timedelta(seconds=options.window_seconds)
    buckets: dict[str, _Bucket] = {}

    for entry in entries:
        if entry.timestamp is None:
            yield entry
            continue

        key = _fingerprint(entry)
        bucket = buckets.get(key)

        if bucket is None:
            bucket = _Bucket(count=1, window_start=entry.timestamp)
            buckets[key] = bucket
            yield entry
            continue

        assert bucket.window_start is not None
        if entry.timestamp - bucket.window_start >= window:
            # Start a fresh window
            bucket.window_start = entry.timestamp
            bucket.count = 1
            yield entry
        elif bucket.count < options.max_per_window:
            bucket.count += 1
            yield entry
        # else: suppressed — limit exceeded within window
