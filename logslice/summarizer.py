"""Summarize a stream of log entries into a compact digest."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry

_SEVERITY_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class SummarizeOptions:
    """Options controlling summary generation."""

    top_n: int = 5  # how many most-frequent messages to include
    include_severity_counts: bool = True
    include_time_range: bool = True

    def __post_init__(self) -> None:
        if self.top_n < 1:
            raise ValueError("top_n must be at least 1")


@dataclass
class LogSummary:
    """Digest produced from a slice of log entries."""

    total: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    top_messages: list[tuple[str, int]] = field(default_factory=list)  # (msg, count)
    earliest: str | None = None
    latest: str | None = None


def summarize_entries(
    entries: Iterable[LogEntry],
    options: SummarizeOptions | None = None,
) -> LogSummary:
    """Consume *entries* and return a :class:`LogSummary`."""
    if options is None:
        options = SummarizeOptions()

    summary = LogSummary()
    message_counts: dict[str, int] = {}

    for entry in entries:
        summary.total += 1

        # severity counts
        if options.include_severity_counts:
            sev = entry.severity or "UNKNOWN"
            summary.severity_counts[sev] = summary.severity_counts.get(sev, 0) + 1

        # time range
        if options.include_time_range and entry.timestamp:
            ts = entry.timestamp
            if summary.earliest is None or ts < summary.earliest:
                summary.earliest = ts
            if summary.latest is None or ts > summary.latest:
                summary.latest = ts

        # message frequency
        msg = entry.message.strip()
        message_counts[msg] = message_counts.get(msg, 0) + 1

    # top-N messages by frequency
    sorted_msgs = sorted(message_counts.items(), key=lambda kv: kv[1], reverse=True)
    summary.top_messages = sorted_msgs[: options.top_n]

    return summary


def iter_summary_lines(summary: LogSummary) -> Iterator[str]:
    """Yield human-readable lines describing *summary*."""
    yield f"Total entries : {summary.total}"

    if summary.earliest or summary.latest:
        yield f"Time range    : {summary.earliest} -> {summary.latest}"

    if summary.severity_counts:
        yield "Severity breakdown:"
        for sev in _SEVERITY_ORDER:
            count = summary.severity_counts.get(sev, 0)
            if count:
                yield f"  {sev:<10} {count}"
        for sev, count in summary.severity_counts.items():
            if sev not in _SEVERITY_ORDER:
                yield f"  {sev:<10} {count}"

    if summary.top_messages:
        yield "Top messages:"
        for msg, count in summary.top_messages:
            short = msg[:72] + "..." if len(msg) > 75 else msg
            yield f"  ({count:>5}x) {short}"
