"""capper.py — Cap entries per severity level within a stream."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry

_SEVERITY_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class CapOptions:
    """Options controlling per-severity entry caps."""

    max_per_severity: int = 0          # 0 means unlimited
    severities: list[str] = field(default_factory=list)  # empty = all

    def __post_init__(self) -> None:
        if self.max_per_severity < 0:
            raise ValueError("max_per_severity must be >= 0")
        normalised = []
        for s in self.severities:
            s_up = s.upper()
            if s_up not in _SEVERITY_ORDER:
                raise ValueError(f"Unknown severity: {s!r}")
            normalised.append(s_up)
        self.severities = normalised


def _should_cap(severity: str, opts: CapOptions) -> bool:
    """Return True if this severity level is subject to capping."""
    if not opts.severities:
        return True
    return severity.upper() in opts.severities


def cap_entries(
    entries: Iterable[LogEntry],
    opts: CapOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries, dropping those that exceed the per-severity cap.

    If *opts* is None or ``max_per_severity`` is 0 every entry is passed
    through unchanged.
    """
    if opts is None or opts.max_per_severity == 0:
        yield from entries
        return

    counts: dict[str, int] = defaultdict(int)

    for entry in entries:
        sev = (entry.severity or "UNKNOWN").upper()
        if _should_cap(sev, opts):
            if counts[sev] >= opts.max_per_severity:
                continue
            counts[sev] += 1
        yield entry
