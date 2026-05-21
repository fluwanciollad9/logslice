"""Aggregates log entries into time buckets for summary reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from logslice.parser import LogEntry


@dataclass
class AggregateOptions:
    bucket_seconds: int = 60
    severity_breakdown: bool = True

    def __post_init__(self) -> None:
        if self.bucket_seconds <= 0:
            raise ValueError("bucket_seconds must be a positive integer")


@dataclass
class Bucket:
    start: datetime
    count: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)

    def record(self, entry: LogEntry) -> None:
        self.count += 1
        sev = entry.severity or "UNKNOWN"
        self.by_severity[sev] = self.by_severity.get(sev, 0) + 1


def _bucket_key(ts: datetime, bucket_seconds: int) -> datetime:
    """Round a timestamp down to the nearest bucket boundary."""
    epoch = datetime(1970, 1, 1, tzinfo=ts.tzinfo)
    delta = int((ts - epoch).total_seconds())
    floored = (delta // bucket_seconds) * bucket_seconds
    return epoch + timedelta(seconds=floored)


def aggregate_entries(
    entries: Iterable[LogEntry],
    options: Optional[AggregateOptions] = None,
) -> List[Bucket]:
    """Group entries into fixed-width time buckets.

    Entries without a timestamp are silently skipped.
    Returns buckets sorted by start time.
    """
    if options is None:
        options = AggregateOptions()

    buckets: Dict[datetime, Bucket] = {}

    for entry in entries:
        if entry.timestamp is None:
            continue
        key = _bucket_key(entry.timestamp, options.bucket_seconds)
        if key not in buckets:
            buckets[key] = Bucket(start=key)
        buckets[key].record(entry)

    return [buckets[k] for k in sorted(buckets)]
