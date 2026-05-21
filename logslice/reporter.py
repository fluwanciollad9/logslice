"""Renders aggregated bucket data as a human-readable summary report."""

from __future__ import annotations

from typing import List, Optional, TextIO
import sys

from logslice.aggregator import Bucket


_SEVERITY_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "UNKNOWN"]


def _bar(count: int, max_count: int, width: int = 20) -> str:
    """Return an ASCII bar proportional to count/max_count."""
    if max_count == 0:
        return ""
    filled = round((count / max_count) * width)
    return "#" * filled + "-" * (width - filled)


def format_report(
    buckets: List[Bucket],
    *,
    show_bar: bool = True,
    severity_breakdown: bool = True,
    time_format: str = "%Y-%m-%d %H:%M:%S",
) -> List[str]:
    """Convert a list of Bucket objects into printable report lines."""
    if not buckets:
        return ["No data to report."]

    max_count = max(b.count for b in buckets)
    lines: List[str] = []

    for bucket in buckets:
        ts_str = bucket.start.strftime(time_format)
        bar_str = f" [{_bar(bucket.count, max_count)}]" if show_bar else ""
        lines.append(f"{ts_str}{bar_str}  {bucket.count} entries")

        if severity_breakdown and bucket.by_severity:
            for sev in _SEVERITY_ORDER:
                cnt = bucket.by_severity.get(sev)
                if cnt:
                    lines.append(f"  {sev:<10} {cnt}")
            for sev, cnt in bucket.by_severity.items():
                if sev not in _SEVERITY_ORDER:
                    lines.append(f"  {sev:<10} {cnt}")

    return lines


def write_report(
    buckets: List[Bucket],
    dest: Optional[TextIO] = None,
    **kwargs,
) -> int:
    """Write a formatted report to *dest* (default: stdout).

    Returns the number of lines written.
    """
    if dest is None:
        dest = sys.stdout
    lines = format_report(buckets, **kwargs)
    for line in lines:
        dest.write(line + "\n")
    return len(lines)
