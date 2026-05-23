"""Resampler: re-bucket log entries into a new time resolution."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Iterator, List

from logslice.parser import LogEntry

_VALID_UNITS = {"second", "minute", "hour"}


@dataclass
class ResampleOptions:
    """Options controlling time-based resampling."""

    unit: str = "minute"
    fill_empty: bool = False

    def __post_init__(self) -> None:
        if self.unit not in _VALID_UNITS:
            raise ValueError(
                f"unit must be one of {sorted(_VALID_UNITS)!r}, got {self.unit!r}"
            )


@dataclass
class ResampledBucket:
    """A single resampled time bucket."""

    bucket_time: datetime
    entries: List[LogEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)


def _truncate(ts: datetime, unit: str) -> datetime:
    """Truncate *ts* to the given unit boundary."""
    if unit == "second":
        return ts.replace(microsecond=0)
    if unit == "minute":
        return ts.replace(second=0, microsecond=0)
    # hour
    return ts.replace(minute=0, second=0, microsecond=0)


def resample_entries(
    entries: Iterable[LogEntry],
    options: ResampleOptions | None = None,
) -> Iterator[ResampledBucket]:
    """Group *entries* into time buckets defined by *options*.

    Entries without a timestamp are silently skipped.
    If ``fill_empty`` is True, a zero-entry bucket is emitted for every
    unit between the first and last observed bucket that contained no
    entries.
    """
    if options is None:
        options = ResampleOptions()

    buckets: dict[datetime, ResampledBucket] = {}

    for entry in entries:
        if entry.timestamp is None:
            continue
        key = _truncate(entry.timestamp, options.unit)
        if key not in buckets:
            buckets[key] = ResampledBucket(bucket_time=key)
        buckets[key].entries.append(entry)

    if not buckets:
        return

    sorted_keys = sorted(buckets)

    if options.fill_empty:
        from datetime import timedelta

        step = timedelta(
            seconds=1 if options.unit == "second" else
            60 if options.unit == "minute" else 3600
        )
        current = sorted_keys[0]
        end = sorted_keys[-1]
        while current <= end:
            if current not in buckets:
                buckets[current] = ResampledBucket(bucket_time=current)
            current += step
        sorted_keys = sorted(buckets)

    for key in sorted_keys:
        yield buckets[key]
