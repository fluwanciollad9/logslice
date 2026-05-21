"""Message truncation utilities for logslice."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry

_DEFAULT_MAX_LENGTH = 200
_ELLIPSIS = "..."


@dataclass
class TruncateOptions:
    """Options controlling how log entry messages are truncated."""

    max_length: int = _DEFAULT_MAX_LENGTH
    ellipsis: str = _ELLIPSIS
    fields: list[str] = field(default_factory=lambda: ["message"])

    def __post_init__(self) -> None:
        if self.max_length < 1:
            raise ValueError(
                f"max_length must be at least 1, got {self.max_length}"
            )
        allowed = {"message", "raw"}
        unknown = set(self.fields) - allowed
        if unknown:
            raise ValueError(
                f"Unknown fields for truncation: {sorted(unknown)}. "
                f"Allowed: {sorted(allowed)}"
            )


def _truncate(text: str, max_length: int, ellipsis: str) -> str:
    """Return *text* truncated to *max_length* characters, appending *ellipsis*."""
    if len(text) <= max_length:
        return text
    cut = max(0, max_length - len(ellipsis))
    return text[:cut] + ellipsis


def truncate_entry(entry: LogEntry, opts: TruncateOptions) -> LogEntry:
    """Return a new :class:`LogEntry` with the requested fields truncated."""
    msg = entry.message
    raw = entry.raw

    if "message" in opts.fields and msg is not None:
        msg = _truncate(msg, opts.max_length, opts.ellipsis)

    if "raw" in opts.fields and raw is not None:
        raw = _truncate(raw, opts.max_length, opts.ellipsis)

    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=msg,
        raw=raw,
    )


def truncate_entries(
    entries: Iterable[LogEntry],
    opts: TruncateOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield truncated copies of each entry in *entries*."""
    if opts is None:
        opts = TruncateOptions()
    for entry in entries:
        yield truncate_entry(entry, opts)
