"""Labeler: attach free-form key/value labels to log entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class LabelOptions:
    """Options controlling how labels are attached to entries."""

    labels: Dict[str, str] = field(default_factory=dict)
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.labels, dict):
            raise TypeError("labels must be a dict")
        for k, v in self.labels.items():
            if not isinstance(k, str) or not k:
                raise ValueError("label keys must be non-empty strings")
            if not isinstance(v, str):
                raise TypeError("label values must be strings")


def label_entry(entry: LogEntry, opts: LabelOptions) -> LogEntry:
    """Return a copy of *entry* with labels merged into its tags."""
    if not opts.labels:
        return entry

    existing: Dict[str, str] = dict(entry.tags) if entry.tags else {}
    for k, v in opts.labels.items():
        if opts.overwrite or k not in existing:
            existing[k] = v

    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=entry.message,
        raw=entry.raw,
        tags=existing,
    )


def label_entries(
    entries: Iterable[LogEntry], opts: LabelOptions
) -> Iterator[LogEntry]:
    """Yield entries with labels applied."""
    for entry in entries:
        yield label_entry(entry, opts)
