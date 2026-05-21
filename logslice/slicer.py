"""Core slicer: streams log files and filters by time range and severity."""

from datetime import datetime
from typing import Generator, Iterable, Optional, Set

from logslice.parser import LogEntry, parse_line

ALL_LEVELS: Set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

SEVERITY_ORDER = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}


def _meets_severity(entry_level: str, min_level: Optional[str]) -> bool:
    if min_level is None:
        return True
    entry_rank = SEVERITY_ORDER.get(entry_level, -1)
    min_rank = SEVERITY_ORDER.get(min_level.upper(), 0)
    return entry_rank >= min_rank


def slice_lines(
    lines: Iterable[str],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_level: Optional[str] = None,
) -> Generator[LogEntry, None, None]:
    """Filter an iterable of raw log lines by time range and minimum severity.

    Args:
        lines:     Iterable of raw log line strings.
        start:     Inclusive lower bound for timestamp filtering.
        end:       Inclusive upper bound for timestamp filtering.
        min_level: Minimum severity level (e.g. "WARNING" includes WARNING+).

    Yields:
        LogEntry objects that pass all filters.
    """
    for line in lines:
        entry = parse_line(line)
        if entry is None:
            continue
        if start is not None and entry.timestamp < start:
            continue
        if end is not None and entry.timestamp > end:
            continue
        if not _meets_severity(entry.level, min_level):
            continue
        yield entry


def slice_file(
    path: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_level: Optional[str] = None,
    encoding: str = "utf-8",
) -> Generator[LogEntry, None, None]:
    """Open a log file and stream filtered entries without loading it fully."""
    with open(path, "r", encoding=encoding, errors="replace") as fh:
        yield from slice_lines(fh, start=start, end=end, min_level=min_level)
