"""Diff consecutive log entries to surface changes between them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from logslice.parser import LogEntry

_VALID_FIELDS = {"message", "severity", "source"}


@dataclass
class DiffOptions:
    enabled: bool = False
    field: str = "message"
    marker_changed: str = "~"
    marker_unchanged: str = " "
    include_unchanged: bool = True

    def __post_init__(self) -> None:
        if self.field not in _VALID_FIELDS:
            raise ValueError(
                f"field must be one of {sorted(_VALID_FIELDS)}, got {self.field!r}"
            )
        if not self.marker_changed:
            raise ValueError("marker_changed must not be empty")
        if not self.marker_unchanged:
            raise ValueError("marker_unchanged must not be empty")


def _get_field(entry: LogEntry, field: str) -> str:
    return str(getattr(entry, field, "") or "")


def diff_entries(
    entries: Iterator[LogEntry],
    options: Optional[DiffOptions] = None,
) -> Iterator[LogEntry]:
    """Yield entries annotated with a diff marker tag.

    Each entry gains a tag ``diff:~`` when its tracked field differs from
    the previous entry, or ``diff: `` when it is unchanged.  Entries with
    ``include_unchanged=False`` and an unchanged field are suppressed.
    """
    if options is None or not options.enabled:
        yield from entries
        return

    prev_value: Optional[str] = None

    for entry in entries:
        current_value = _get_field(entry, options.field)
        changed = prev_value is None or current_value != prev_value
        prev_value = current_value

        if not changed and not options.include_unchanged:
            continue

        marker = options.marker_changed if changed else options.marker_unchanged
        tags: List[str] = list(entry.tags or [])
        # Remove stale diff tag if present
        tags = [t for t in tags if not t.startswith("diff:")]
        tags.append(f"diff:{marker}")

        yield LogEntry(
            timestamp=entry.timestamp,
            severity=entry.severity,
            message=entry.message,
            source=entry.source,
            raw=entry.raw,
            tags=tags,
        )
