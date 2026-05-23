"""Flattener: expand multi-line log entries into individual single-line entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class FlattenOptions:
    """Options controlling how multi-line entries are split."""

    enabled: bool = False
    separator: str = "\n"
    strip_lines: bool = True
    skip_empty: bool = True
    tag_index: bool = False  # add a 'line_index' tag to each emitted entry

    def __post_init__(self) -> None:
        if not self.separator:
            raise ValueError("separator must be a non-empty string")


def _split_message(message: str, opts: FlattenOptions) -> list[str]:
    parts = message.split(opts.separator)
    if opts.strip_lines:
        parts = [p.strip() for p in parts]
    if opts.skip_empty:
        parts = [p for p in parts if p]
    return parts


def flatten_entry(entry: LogEntry, opts: FlattenOptions) -> Iterator[LogEntry]:
    """Yield one LogEntry per line found in *entry.message*."""
    parts = _split_message(entry.message, opts)
    if not parts:
        return
    for idx, part in enumerate(parts):
        tags = dict(entry.tags) if entry.tags else {}
        if opts.tag_index:
            tags["line_index"] = str(idx)
        yield LogEntry(
            timestamp=entry.timestamp,
            severity=entry.severity,
            message=part,
            raw=entry.raw,
            tags=tags if tags else None,
        )


def flatten_entries(
    entries: Iterable[LogEntry], opts: FlattenOptions
) -> Iterator[LogEntry]:
    """Apply flattening to a stream of entries."""
    if not opts.enabled:
        yield from entries
        return
    for entry in entries:
        yield from flatten_entry(entry, opts)
