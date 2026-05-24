"""Join multi-line log entries into single logical entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class JoinOptions:
    """Options controlling how continuation lines are joined."""

    # Regex pattern that identifies a *continuation* line (not a new entry).
    continuation_pattern: str = r"^\s+"
    # String inserted between joined lines.
    separator: str = " "
    # Maximum number of continuation lines to absorb into one entry.
    max_lines: int = 50

    def __post_init__(self) -> None:
        import re

        if not self.continuation_pattern:
            raise ValueError("continuation_pattern must not be empty")
        if self.max_lines < 1:
            raise ValueError("max_lines must be at least 1")
        if self.separator is None:
            raise ValueError("separator must not be None")
        # Validate the regex compiles.
        re.compile(self.continuation_pattern)


def join_entries(
    entries: Iterable[LogEntry | None],
    options: JoinOptions | None = None,
) -> Iterator[LogEntry]:
    """Merge continuation lines into the preceding parsed entry.

    ``None`` values (unparseable raw lines forwarded by the slicer) are
    treated as continuation lines when they match *continuation_pattern*;
    otherwise they are discarded.
    """
    import re

    opts = options or JoinOptions()
    pattern = re.compile(opts.continuation_pattern)
    pending: LogEntry | None = None
    absorbed: int = 0

    for entry in entries:
        if entry is None:
            continue

        # Detect whether this is really a continuation masquerading as a
        # parsed entry (e.g. a line that matched the timestamp regex but
        # whose message starts with whitespace).
        if pending is not None and pattern.match(entry.message) and absorbed < opts.max_lines:
            joined_message = pending.message + opts.separator + entry.message.strip()
            pending = LogEntry(
                timestamp=pending.timestamp,
                severity=pending.severity,
                message=joined_message,
                raw=pending.raw + opts.separator + entry.raw,
                tags=pending.tags,
            )
            absorbed += 1
        else:
            if pending is not None:
                yield pending
            pending = entry
            absorbed = 0

    if pending is not None:
        yield pending
