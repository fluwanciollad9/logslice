"""Log line parser: extracts timestamp and severity from common log formats."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Matches: 2024-01-15 12:34:56,789 [ERROR] Some message
PATTERN_STANDARD = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
    r"\s*\[?(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\]?"
    r"\s*(?P<message>.*)",
    re.IGNORECASE,
)

TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S",
]

SEVERITY_ALIASES = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
}


@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    message: str
    raw: str


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Try to parse a timestamp string using known formats."""
    ts_str = ts_str.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def parse_line(line: str) -> Optional[LogEntry]:
    """Parse a single log line into a LogEntry, or return None if unparseable."""
    line = line.rstrip("\n")
    match = PATTERN_STANDARD.match(line)
    if not match:
        return None

    ts = parse_timestamp(match.group("ts"))
    if ts is None:
        return None

    level = match.group("level").upper()
    level = SEVERITY_ALIASES.get(level, level)

    return LogEntry(
        timestamp=ts,
        level=level,
        message=match.group("message").strip(),
        raw=line,
    )
