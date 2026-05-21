"""Statistics collection for log slicing operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SliceStats:
    """Aggregated statistics produced during a slice operation."""

    total_lines: int = 0
    matched_lines: int = 0
    skipped_unparseable: int = 0
    skipped_severity: int = 0
    skipped_before_start: int = 0
    skipped_after_end: int = 0
    severity_counts: Dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Derived helpers
    # ------------------------------------------------------------------ #

    @property
    def skipped_lines(self) -> int:
        """Total number of lines that were *not* emitted."""
        return self.total_lines - self.matched_lines

    @property
    def match_rate(self) -> Optional[float]:
        """Fraction of parseable lines that matched all filters (0‒1)."""
        parseable = self.total_lines - self.skipped_unparseable
        if parseable == 0:
            return None
        return self.matched_lines / parseable

    # ------------------------------------------------------------------ #
    # Mutation helpers (called by slicer internals)
    # ------------------------------------------------------------------ #

    def record_match(self, severity: str) -> None:
        """Register a line that passed every filter."""
        self.total_lines += 1
        self.matched_lines += 1
        self.severity_counts[severity] = self.severity_counts.get(severity, 0) + 1

    def record_unparseable(self) -> None:
        self.total_lines += 1
        self.skipped_unparseable += 1

    def record_severity_skip(self, severity: str) -> None:
        self.total_lines += 1
        self.skipped_severity += 1
        self.severity_counts[severity] = self.severity_counts.get(severity, 0) + 1

    def record_time_skip(self, *, before: bool) -> None:
        self.total_lines += 1
        if before:
            self.skipped_before_start += 1
        else:
            self.skipped_after_end += 1

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #

    def summary(self) -> str:
        """Return a human-readable one-block summary string."""
        rate = self.match_rate
        rate_str = f"{rate:.1%}" if rate is not None else "n/a"
        lines = [
            f"Total lines      : {self.total_lines}",
            f"Matched          : {self.matched_lines}  ({rate_str})",
            f"Skipped total    : {self.skipped_lines}",
            f"  unparseable    : {self.skipped_unparseable}",
            f"  severity       : {self.skipped_severity}",
            f"  before start   : {self.skipped_before_start}",
            f"  after end      : {self.skipped_after_end}",
        ]
        if self.severity_counts:
            lines.append("Severity breakdown:")
            for sev, cnt in sorted(self.severity_counts.items()):
                lines.append(f"  {sev:<10}: {cnt}")
        return "\n".join(lines)
