"""Entry sorting for logslice pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, List

from logslice.parser import LogEntry

_VALID_KEYS = {"timestamp", "severity", "message"}
_VALID_ORDERS = {"asc", "desc"}


@dataclass
class SortOptions:
    """Options controlling how entries are sorted."""

    key: str = "timestamp"
    order: str = "asc"
    stable: bool = True

    def __post_init__(self) -> None:
        if self.key not in _VALID_KEYS:
            raise ValueError(
                f"Invalid sort key {self.key!r}. Must be one of {sorted(_VALID_KEYS)}."
            )
        if self.order not in _VALID_ORDERS:
            raise ValueError(
                f"Invalid sort order {self.order!r}. Must be 'asc' or 'desc'."
            )


def _entry_key(entry: LogEntry, key: str):
    """Return the sort key value for *entry*."""
    if key == "timestamp":
        # None timestamps sort to the beginning
        return (0, "") if entry.timestamp is None else (1, entry.timestamp.isoformat())
    if key == "severity":
        return entry.severity or ""
    return entry.message or ""


def sort_entries(
    entries: Iterable[LogEntry],
    opts: SortOptions | None = None,
) -> Iterator[LogEntry]:
    """Sort *entries* according to *opts* and yield them in order.

    Note: this buffers all entries in memory.
    """
    if opts is None:
        opts = SortOptions()

    buffered: List[LogEntry] = list(entries)
    reverse = opts.order == "desc"
    buffered.sort(
        key=lambda e: _entry_key(e, opts.key),
        reverse=reverse,
    )
    yield from buffered
