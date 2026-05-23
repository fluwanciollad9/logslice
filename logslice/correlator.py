"""Correlate log entries by matching a shared field value within a time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Iterator, List, Optional

from logslice.parser import LogEntry

_VALID_FIELDS = {"severity", "source", "tag"}


@dataclass
class CorrelateOptions:
    """Options controlling entry correlation."""

    field: str = "tag"
    key: str = ""
    window_seconds: float = 60.0
    min_matches: int = 2

    def __post_init__(self) -> None:
        if self.field not in _VALID_FIELDS:
            raise ValueError(
                f"field must be one of {sorted(_VALID_FIELDS)}, got {self.field!r}"
            )
        if not self.key:
            raise ValueError("key must be a non-empty string")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.min_matches < 1:
            raise ValueError("min_matches must be at least 1")


def _get_field(entry: LogEntry, field_name: str) -> Optional[str]:
    if field_name == "severity":
        return entry.severity
    if field_name == "source":
        return entry.source
    if field_name == "tag":
        tags: dict = getattr(entry, "tags", {}) or {}
        return tags.get("tag")
    return None


def correlate_entries(
    entries: Iterable[LogEntry],
    opts: CorrelateOptions,
) -> Iterator[List[LogEntry]]:
    """Yield groups of entries whose *field* equals *key* within *window_seconds*.

    Only groups with at least *min_matches* entries are emitted.
    """
    window = timedelta(seconds=opts.window_seconds)
    bucket: List[LogEntry] = []

    for entry in entries:
        value = _get_field(entry, opts.field)
        if value != opts.key:
            continue

        ts: Optional[datetime] = entry.timestamp
        if ts is None:
            bucket.append(entry)
            continue

        # Flush entries that have fallen outside the window
        if bucket:
            anchor: Optional[datetime] = next(
                (e.timestamp for e in bucket if e.timestamp is not None), None
            )
            if anchor is not None and (ts - anchor) > window:
                if len(bucket) >= opts.min_matches:
                    yield list(bucket)
                bucket = []

        bucket.append(entry)

    if len(bucket) >= opts.min_matches:
        yield list(bucket)
