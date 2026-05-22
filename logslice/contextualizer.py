"""Context lines: capture N lines before/after each matching log entry."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ContextOptions:
    before: int = 0
    after: int = 0

    def __post_init__(self) -> None:
        if self.before < 0:
            raise ValueError("before must be >= 0")
        if self.after < 0:
            raise ValueError("after must be >= 0")


def contextualize_entries(
    entries: Iterable[LogEntry],
    matched: set[int],
    options: ContextOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries that are matches or fall within context windows.

    *matched* is a set of indices (0-based) into *entries* that are considered
    direct matches.  Entries within *options.before* lines before or
    *options.after* lines after a match are also yielded, deduplicated and in
    original order.
    """
    if options is None:
        options = ContextOptions()

    all_entries: list[LogEntry] = list(entries)
    if not all_entries:
        return

    include: set[int] = set()
    for idx in matched:
        start = max(0, idx - options.before)
        end = min(len(all_entries) - 1, idx + options.after)
        for i in range(start, end + 1):
            include.add(i)

    for i, entry in enumerate(all_entries):
        if i in include:
            yield entry


def sliding_context(
    entries: Iterable[LogEntry],
    predicate,
    options: ContextOptions | None = None,
) -> Iterator[LogEntry]:
    """Stream-friendly context window that avoids loading all entries.

    Yields entries whose index falls within the context window of any entry
    for which *predicate(entry)* returns True.  Uses a look-behind buffer for
    *before* lines and a countdown for *after* lines.
    """
    if options is None:
        options = ContextOptions()

    before_buf: deque[LogEntry] = deque(maxlen=options.before or 1)
    pending: list[LogEntry] = []
    after_countdown: int = 0
    emitted_ids: set[int] = set()

    def _emit(e: LogEntry) -> Iterator[LogEntry]:
        eid = id(e)
        if eid not in emitted_ids:
            emitted_ids.add(eid)
            yield e

    for entry in entries:
        if predicate(entry):
            # flush before-buffer
            for buf_entry in before_buf:
                yield from _emit(buf_entry)
            before_buf.clear()
            yield from _emit(entry)
            after_countdown = options.after
        elif after_countdown > 0:
            yield from _emit(entry)
            after_countdown -= 1
        else:
            if options.before > 0:
                before_buf.append(entry)
