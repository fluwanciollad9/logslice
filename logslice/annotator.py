"""Annotate log entries with sequential line numbers or custom prefixes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class AnnotateOptions:
    enabled: bool = False
    prefix: str = "#"
    start: int = 1
    step: int = 1
    tag_key: str = "lineno"

    def __post_init__(self) -> None:
        if self.step < 1:
            raise ValueError("step must be >= 1")
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if not self.tag_key:
            raise ValueError("tag_key must not be empty")


def annotate_entries(
    entries: Iterable[LogEntry],
    options: AnnotateOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries annotated with a sequential line number tag.

    The annotation is stored in ``entry.tags`` under *options.tag_key* and
    also prepended to ``entry.message`` when *options.prefix* is non-empty.
    """
    if options is None or not options.enabled:
        yield from entries
        return

    counter = options.start
    for entry in entries:
        tags = dict(entry.tags) if entry.tags else {}
        tags[options.tag_key] = str(counter)

        if options.prefix:
            annotated_message = f"{options.prefix}{counter} {entry.message}"
        else:
            annotated_message = entry.message

        yield LogEntry(
            timestamp=entry.timestamp,
            severity=entry.severity,
            message=annotated_message,
            raw=entry.raw,
            tags=tags,
        )
        counter += options.step
