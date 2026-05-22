"""Field-level message transformer for log entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class TransformOptions:
    """Options controlling per-field transformations applied to log entries."""

    message_transforms: list[Callable[[str], str]] = field(default_factory=list)
    severity_transforms: list[Callable[[str], str]] = field(default_factory=list)
    source_transforms: list[Callable[[str], str]] = field(default_factory=list)
    drop_fields: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        valid_fields = {"message", "severity", "source", "tags"}
        unknown = self.drop_fields - valid_fields
        if unknown:
            raise ValueError(
                f"Unknown drop_fields: {sorted(unknown)}. "
                f"Valid fields are: {sorted(valid_fields)}"
            )


def _apply(value: str, transforms: list[Callable[[str], str]]) -> str:
    for fn in transforms:
        value = fn(value)
    return value


def transform_entry(entry: LogEntry, opts: TransformOptions) -> LogEntry:
    """Return a new LogEntry with transformations applied."""
    message = (
        ""
        if "message" in opts.drop_fields
        else _apply(entry.message, opts.message_transforms)
    )
    severity = (
        ""
        if "severity" in opts.drop_fields
        else _apply(entry.severity, opts.severity_transforms)
    )
    source = (
        None
        if "source" in opts.drop_fields
        else (
            _apply(entry.source, opts.source_transforms)
            if entry.source is not None
            else None
        )
    )
    tags = set() if "tags" in opts.drop_fields else set(entry.tags)
    return LogEntry(
        timestamp=entry.timestamp,
        severity=severity,
        message=message,
        source=source,
        raw=entry.raw,
        tags=tags,
    )


def transform_entries(
    entries: Iterable[LogEntry], opts: TransformOptions
) -> Iterator[LogEntry]:
    """Yield transformed copies of each entry."""
    for entry in entries:
        yield transform_entry(entry, opts)
