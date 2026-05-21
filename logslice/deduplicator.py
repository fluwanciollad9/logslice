"""Deduplication support for log entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import md5
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class DedupeOptions:
    """Options controlling deduplication behaviour."""

    enabled: bool = False
    # Consider only message text when fingerprinting (ignore timestamp).
    message_only: bool = True
    # Maximum number of fingerprints to keep in memory.
    max_cache: int = 10_000

    def __post_init__(self) -> None:
        if self.max_cache < 1:
            raise ValueError("max_cache must be at least 1")


def _fingerprint(entry: LogEntry, message_only: bool) -> str:
    """Return a short hash that identifies a log entry."""
    if message_only:
        key = f"{entry.severity}:{entry.message}"
    else:
        key = f"{entry.timestamp}:{entry.severity}:{entry.message}"
    return md5(key.encode(), usedforsecurity=False).hexdigest()  # noqa: S324


def deduplicate_entries(
    entries: Iterable[LogEntry],
    options: DedupeOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield only the first occurrence of each distinct log entry.

    When *options* is ``None`` or ``options.enabled`` is ``False`` every
    entry is passed through unchanged.
    """
    if options is None or not options.enabled:
        yield from entries
        return

    seen: dict[str, int] = {}
    for entry in entries:
        fp = _fingerprint(entry, options.message_only)
        if fp not in seen:
            seen[fp] = 1
            # Evict oldest entries when cache is full.
            if len(seen) > options.max_cache:
                oldest = next(iter(seen))
                del seen[oldest]
            yield entry
        else:
            seen[fp] += 1


def duplicate_counts(
    entries: Iterable[LogEntry],
    options: DedupeOptions | None = None,
) -> dict[str, int]:
    """Return a mapping of fingerprint -> occurrence count for *entries*.

    Useful for reporting how many duplicates were suppressed.
    """
    opts = options or DedupeOptions(enabled=True)
    counts: dict[str, int] = {}
    for entry in entries:
        fp = _fingerprint(entry, opts.message_only)
        counts[fp] = counts.get(fp, 0) + 1
    return counts
