"""Compactor: collapse consecutive duplicate or near-duplicate log entries into a single entry with a repeat count."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class CompactOptions:
    """Options controlling compaction behaviour."""
    max_gap_seconds: float = 5.0   # max time between entries to still consider them consecutive
    case_sensitive: bool = False
    repeat_tag: str = "repeated"    # tag key used to store the repeat count

    def __post_init__(self) -> None:
        if self.max_gap_seconds < 0:
            raise ValueError("max_gap_seconds must be >= 0")
        if not self.repeat_tag:
            raise ValueError("repeat_tag must not be empty")


def _messages_match(a: str, b: str, case_sensitive: bool) -> bool:
    if case_sensitive:
        return a == b
    return a.lower() == b.lower()


def _gap_ok(prev: LogEntry, curr: LogEntry, max_gap: float) -> bool:
    """Return True when timestamps are close enough (or either is missing)."""
    if prev.timestamp is None or curr.timestamp is None:
        return True
    return abs((curr.timestamp - prev.timestamp).total_seconds()) <= max_gap


def compact_entries(
    entries: Iterable[LogEntry],
    options: CompactOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield compacted entries; consecutive identical messages are merged.

    The first entry of a run is emitted with a ``repeat_tag`` tag set to the
    total count of occurrences (including itself).  Runs of length 1 are
    emitted without the tag so the output is identical to the input when
    nothing repeats.
    """
    opts = options or CompactOptions()
    pending: LogEntry | None = None
    run: int = 0

    for entry in entries:
        if pending is None:
            pending = entry
            run = 1
            continue

        same_severity = pending.severity == entry.severity
        same_message = _messages_match(pending.message, entry.message, opts.case_sensitive)
        within_gap = _gap_ok(pending, entry, opts.max_gap_seconds)

        if same_severity and same_message and within_gap:
            run += 1
        else:
            yield _emit(pending, run, opts.repeat_tag)
            pending = entry
            run = 1

    if pending is not None:
        yield _emit(pending, run, opts.repeat_tag)


def _emit(entry: LogEntry, run: int, repeat_tag: str) -> LogEntry:
    if run == 1:
        return entry
    tags = dict(entry.tags) if entry.tags else {}
    tags[repeat_tag] = str(run)
    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=entry.message,
        raw=entry.raw,
        tags=tags,
    )
