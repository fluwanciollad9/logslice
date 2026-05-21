"""Core slicing logic: filter log lines by time range and severity."""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Generator, Iterable, Optional, Tuple

from logslice.parser import LogEntry, parse_line
from logslice.stats import SliceStats

# Severity ordering (lowest → highest)
_SEVERITY_ORDER = [
    "debug",
    "info",
    "warning",
    "error",
    "critical",
]


def _meets_severity(entry_severity: str, min_severity: Optional[str]) -> bool:
    """Return True when *entry_severity* is at or above *min_severity*."""
    if min_severity is None:
        return True
    try:
        entry_idx = _SEVERITY_ORDER.index(entry_severity.lower())
        min_idx = _SEVERITY_ORDER.index(min_severity.lower())
    except ValueError:
        return True
    return entry_idx >= min_idx


def slice_lines(
    lines: Iterable[str],
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_severity: Optional[str] = None,
    collect_stats: bool = False,
) -> Tuple[Generator[LogEntry, None, None], Optional[SliceStats]]:
    """Filter *lines* and yield matching :class:`LogEntry` objects.

    Returns a ``(generator, stats)`` pair.  *stats* is a
    :class:`~logslice.stats.SliceStats` instance when *collect_stats* is
    ``True``, otherwise ``None``.
    """
    stats: Optional[SliceStats] = SliceStats() if collect_stats else None

    def _generate() -> Generator[LogEntry, None, None]:
        for raw in lines:
            entry = parse_line(raw.rstrip("\n"))
            if entry is None:
                if stats is not None:
                    stats.record_unparseable()
                continue
            if start is not None and entry.timestamp < start:
                if stats is not None:
                    stats.record_time_skip(before=True)
                continue
            if end is not None and entry.timestamp > end:
                if stats is not None:
                    stats.record_time_skip(before=False)
                continue
            if not _meets_severity(entry.severity, min_severity):
                if stats is not None:
                    stats.record_severity_skip(entry.severity)
                continue
            if stats is not None:
                stats.record_match(entry.severity)
            yield entry

    return _generate(), stats


def slice_file(
    path: str,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    min_severity: Optional[str] = None,
    collect_stats: bool = False,
) -> Tuple[Generator[LogEntry, None, None], Optional[SliceStats]]:
    """Open *path* and return a ``(generator, stats)`` pair via
    :func:`slice_lines`.
    """
    try:
        fh = open(path, "r", encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"logslice: cannot open '{path}': {exc}", file=sys.stderr)
        sys.exit(1)

    gen, stats = slice_lines(
        fh,
        start=start,
        end=end,
        min_severity=min_severity,
        collect_stats=collect_stats,
    )

    # Wrap generator so the file handle is closed after exhaustion
    def _wrap() -> Generator[LogEntry, None, None]:
        try:
            yield from gen
        finally:
            fh.close()

    return _wrap(), stats
