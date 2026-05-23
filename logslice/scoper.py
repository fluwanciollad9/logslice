"""Scope entries by line number or entry index ranges."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ScopeOptions:
    """Options controlling index-based scoping of log entries."""

    start: int = 0
    """Inclusive zero-based index of the first entry to keep."""

    stop: int | None = None
    """Exclusive zero-based index of the last entry to keep (None = no limit)."""

    step: int = 1
    """Keep every *step*-th entry within the range (1 = keep all)."""

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.stop is not None and self.stop < self.start:
            raise ValueError("stop must be >= start")
        if self.step < 1:
            raise ValueError("step must be >= 1")


def scope_entries(
    entries: Iterable[LogEntry],
    options: ScopeOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries whose index falls within *options* range.

    Parameters
    ----------
    entries:
        Source stream of :class:`~logslice.parser.LogEntry` objects.
    options:
        Scoping configuration.  When *None* all entries are yielded unchanged.
    """
    if options is None:
        yield from entries
        return

    start = options.start
    stop = options.stop
    step = options.step

    for idx, entry in enumerate(entries):
        if stop is not None and idx >= stop:
            break
        if idx < start:
            continue
        if (idx - start) % step == 0:
            yield entry
