"""Entry profiler: measures per-severity and per-minute throughput."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ProfileOptions:
    bucket_seconds: int = 60
    include_rate: bool = True

    def __post_init__(self) -> None:
        if self.bucket_seconds <= 0:
            raise ValueError("bucket_seconds must be positive")


@dataclass
class ProfileResult:
    severity_counts: dict[str, int] = field(default_factory=dict)
    bucket_counts: dict[str, int] = field(default_factory=dict)  # ISO minute-key -> count
    total: int = 0

    def top_severity(self) -> str | None:
        if not self.severity_counts:
            return None
        return max(self.severity_counts, key=lambda k: self.severity_counts[k])

    def peak_bucket(self) -> str | None:
        if not self.bucket_counts:
            return None
        return max(self.bucket_counts, key=lambda k: self.bucket_counts[k])


def _bucket_key(ts: datetime, bucket_seconds: int) -> str:
    epoch = int(ts.replace(tzinfo=timezone.utc).timestamp())
    slot = (epoch // bucket_seconds) * bucket_seconds
    return datetime.utcfromtimestamp(slot).strftime("%Y-%m-%dT%H:%M:%S")


def profile_entries(
    entries: Iterable[LogEntry],
    opts: ProfileOptions | None = None,
) -> tuple[Iterator[LogEntry], ProfileResult]:
    """Consume *entries*, build a ProfileResult, and re-yield each entry."""
    if opts is None:
        opts = ProfileOptions()
    result = ProfileResult()
    collected: list[LogEntry] = []
    for entry in entries:
        collected.append(entry)
        result.total += 1
        sev = entry.severity or "UNKNOWN"
        result.severity_counts[sev] = result.severity_counts.get(sev, 0) + 1
        if opts.include_rate and entry.timestamp is not None:
            key = _bucket_key(entry.timestamp, opts.bucket_seconds)
            result.bucket_counts[key] = result.bucket_counts.get(key, 0) + 1
    return iter(collected), result
