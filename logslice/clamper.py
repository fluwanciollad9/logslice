"""Clamp log entry messages and fields to defined value ranges."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class ClampOptions:
    """Options controlling how numeric-like severity levels are clamped."""

    min_severity: str | None = None  # drop entries below this severity
    max_severity: str | None = None  # drop entries above this severity
    allowed_severities: list[str] = field(default_factory=list)

    # Ordered from lowest to highest for range comparisons.
    _SEVERITY_ORDER: list[str] = field(
        default_factory=lambda: [
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        ],
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        order = self._SEVERITY_ORDER
        if self.min_severity is not None:
            norm = self.min_severity.lower()
            if norm not in order:
                raise ValueError(
                    f"min_severity {self.min_severity!r} is not a known severity level"
                )
            self.min_severity = norm
        if self.max_severity is not None:
            norm = self.max_severity.lower()
            if norm not in order:
                raise ValueError(
                    f"max_severity {self.max_severity!r} is not a known severity level"
                )
            self.max_severity = norm
        if self.min_severity and self.max_severity:
            if order.index(self.min_severity) > order.index(self.max_severity):
                raise ValueError(
                    "min_severity must not be higher than max_severity"
                )
        self.allowed_severities = [
            s.lower() for s in self.allowed_severities
        ]


def _within_range(severity: str, opts: ClampOptions) -> bool:
    """Return True if *severity* falls within the configured clamp range."""
    order = opts._SEVERITY_ORDER
    norm = severity.lower()

    if opts.allowed_severities and norm not in opts.allowed_severities:
        return False

    rank = order.index(norm) if norm in order else -1

    if opts.min_severity is not None:
        if rank < order.index(opts.min_severity):
            return False
    if opts.max_severity is not None:
        if rank > order.index(opts.max_severity):
            return False
    return True


def clamp_entries(
    entries: Iterable[LogEntry],
    opts: ClampOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield only entries whose severity falls within *opts* bounds."""
    if opts is None:
        opts = ClampOptions()
    for entry in entries:
        if entry.severity and not _within_range(entry.severity, opts):
            continue
        yield entry
