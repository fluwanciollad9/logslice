"""Parse raw log lines into structured LogEntry objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Severity aliases normalised to canonical names
_SEVERITY_ALIASES: dict[str, str] = {
    "warn": "WARNING",
    "warning": "WARNING",
    "err": "ERROR",
    "error": "ERROR",
    "info": "INFO",
    "debug": "DEBUG",
    "critical": "CRITICAL",
    "crit": "CRITICAL",
    "fatal": "CRITICAL",
}

_LINE_RE = re.compile(
    r"^(?P<ts>[\d\-T :./]+)\s+"
    r"(?P<sev>[A-Za-z]+)\s+"
    r"(?P<msg>.+)$"
)

_TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


@dataclass
class LogEntry:
    timestamp: Optional[datetime]
    severity: Optional[str]
    message: str
    raw: str
    tags: list[str] = field(default_factory=list)


def parse_timestamp(value: str) -> Optional[datetime]:
    value = value.strip()
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_line(line: str) -> Optional[LogEntry]:
    line = line.rstrip("\n")
    m = _LINE_RE.match(line)
    if not m:
        return None
    ts = parse_timestamp(m.group("ts"))
    raw_sev = m.group("sev").lower()
    severity = _SEVERITY_ALIASES.get(raw_sev, raw_sev.upper())
    return LogEntry(
        timestamp=ts,
        severity=severity,
        message=m.group("msg").strip(),
        raw=line,
    )
