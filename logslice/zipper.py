"""Zipper: interleave two sorted entry streams by timestamp."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ZipOptions:
    """Options controlling how two entry streams are zipped together."""

    key: str = "timestamp"  # field used for ordering: 'timestamp' or 'severity'
    order: str = "asc"       # 'asc' or 'desc'
    tag_left: str = ""       # optional tag applied to entries from the left stream
    tag_right: str = ""      # optional tag applied to entries from the right stream

    def __post_init__(self) -> None:
        if self.key not in ("timestamp", "severity"):
            raise ValueError(f"key must be 'timestamp' or 'severity', got {self.key!r}")
        if self.order not in ("asc", "desc"):
            raise ValueError(f"order must be 'asc' or 'desc', got {self.order!r}")


def _entry_key(entry: LogEntry, key: str):
    if key == "timestamp":
        return entry.timestamp or ""
    severity_rank = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    return severity_rank.get((entry.severity or "").upper(), -1)


def _tag(entry: LogEntry, label: str) -> LogEntry:
    if not label:
        return entry
    existing = entry.tags or []
    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=entry.message,
        raw=entry.raw,
        tags=list(existing) + [label],
    )


def zip_entries(
    left: Iterable[LogEntry],
    right: Iterable[LogEntry],
    options: ZipOptions | None = None,
) -> Iterator[LogEntry]:
    """Merge-sort two entry streams into a single interleaved stream."""
    opts = options or ZipOptions()
    reverse = opts.order == "desc"

    left_tagged = (_tag(e, opts.tag_left) for e in left)
    right_tagged = (_tag(e, opts.tag_right) for e in right)

    left_iter = iter(left_tagged)
    right_iter = iter(right_tagged)

    sentinel = object()
    l_entry = next(left_iter, sentinel)
    r_entry = next(right_iter, sentinel)

    while l_entry is not sentinel and r_entry is not sentinel:
        lk = _entry_key(l_entry, opts.key)  # type: ignore[arg-type]
        rk = _entry_key(r_entry, opts.key)  # type: ignore[arg-type]
        pick_left = (lk <= rk) if not reverse else (lk >= rk)
        if pick_left:
            yield l_entry  # type: ignore[misc]
            l_entry = next(left_iter, sentinel)
        else:
            yield r_entry  # type: ignore[misc]
            r_entry = next(right_iter, sentinel)

    while l_entry is not sentinel:
        yield l_entry  # type: ignore[misc]
        l_entry = next(left_iter, sentinel)

    while r_entry is not sentinel:
        yield r_entry  # type: ignore[misc]
        r_entry = next(right_iter, sentinel)
