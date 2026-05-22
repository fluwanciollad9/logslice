"""Group log entries by a field and yield (key, entries) pairs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator, Iterable, Iterator

from logslice.parser import LogEntry

_VALID_BY = {"severity", "tag", "source"}


@dataclass
class GroupOptions:
    by: str = "severity"
    sort_keys: bool = True

    def __post_init__(self) -> None:
        if self.by not in _VALID_BY:
            raise ValueError(
                f"Invalid group-by field {self.by!r}. "
                f"Choose from: {sorted(_VALID_BY)}"
            )


def _entry_key(entry: LogEntry, by: str) -> str:
    if by == "severity":
        return entry.severity or "UNKNOWN"
    if by == "tag":
        tags = getattr(entry, "tags", None)
        if tags:
            return ",".join(sorted(tags))
        return "(untagged)"
    if by == "source":
        return getattr(entry, "source", None) or "(unknown)"
    return "(unknown)"  # pragma: no cover


def group_entries(
    entries: Iterable[LogEntry],
    options: GroupOptions | None = None,
) -> dict[str, list[LogEntry]]:
    """Collect entries into a dict keyed by the chosen field."""
    opts = options or GroupOptions()
    groups: dict[str, list[LogEntry]] = {}
    for entry in entries:
        key = _entry_key(entry, opts.by)
        groups.setdefault(key, []).append(entry)
    return groups


def iter_group_entries(
    entries: Iterable[LogEntry],
    options: GroupOptions | None = None,
) -> Iterator[tuple[str, list[LogEntry]]]:
    """Yield (key, group) pairs, optionally with sorted keys."""
    opts = options or GroupOptions()
    groups = group_entries(entries, opts)
    keys = sorted(groups) if opts.sort_keys else list(groups)
    for key in keys:
        yield key, groups[key]
