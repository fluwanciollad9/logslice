"""Alert on entries matching threshold conditions within a time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Generator, Iterable, List

from logslice.parser import LogEntry

_SEVERITIES = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class AlertOptions:
    severity: str = "ERROR"
    threshold: int = 3
    window_seconds: float = 60.0
    alert_tag: str = "ALERT"

    def __post_init__(self) -> None:
        sev = self.severity.upper()
        if sev not in _SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity!r}")
        self.severity = sev
        if self.threshold < 1:
            raise ValueError("threshold must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if not self.alert_tag:
            raise ValueError("alert_tag must not be empty")


@dataclass
class AlertEvent:
    triggered_at: datetime
    severity: str
    count: int
    window_seconds: float
    entries: List[LogEntry] = field(default_factory=list)


def alert_entries(
    entries: Iterable[LogEntry],
    opts: AlertOptions | None = None,
) -> Generator[LogEntry, None, None]:
    """Yield entries unchanged; attach alert_tag to those that breach threshold."""
    if opts is None:
        opts = AlertOptions()

    sev_rank = _SEVERITIES.index(opts.severity)
    window = timedelta(seconds=opts.window_seconds)
    bucket: List[LogEntry] = []
    alerted: set = set()

    for entry in entries:
        rank = _SEVERITIES.index(entry.severity) if entry.severity in _SEVERITIES else -1
        if rank >= sev_rank and entry.timestamp is not None:
            bucket = [e for e in bucket if entry.timestamp - e.timestamp <= window]  # type: ignore[operator]
            bucket.append(entry)
            if len(bucket) >= opts.threshold:
                for e in bucket:
                    eid = id(e)
                    if eid not in alerted:
                        alerted.add(eid)
                        tags = dict(e.extra)
                        tags[opts.alert_tag] = "true"
                        entry = LogEntry(
                            timestamp=e.timestamp,
                            severity=e.severity,
                            message=e.message,
                            raw=e.raw,
                            extra=tags,
                        )
                        yield entry
                        continue
                yield entry
                continue
        yield entry
