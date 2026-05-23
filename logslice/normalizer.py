"""Normalizer: standardise field values across log entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry

_SEVERITY_ALIASES: dict[str, str] = {
    "warn": "WARNING",
    "warning": "WARNING",
    "err": "ERROR",
    "error": "ERROR",
    "crit": "CRITICAL",
    "critical": "CRITICAL",
    "info": "INFO",
    "debug": "DEBUG",
    "trace": "DEBUG",
    "fatal": "CRITICAL",
}

_VALID_FIELDS = frozenset({"severity", "message", "source"})


@dataclass
class NormalizeOptions:
    """Options controlling field normalisation."""

    severity: bool = True
    strip_message: bool = True
    uppercase_source: bool = False
    extra_severity_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for raw, mapped in self.extra_severity_map.items():
            if not isinstance(raw, str) or not raw:
                raise ValueError("extra_severity_map keys must be non-empty strings")
            if not isinstance(mapped, str) or not mapped:
                raise ValueError("extra_severity_map values must be non-empty strings")


def _normalize_severity(severity: str, extra: dict[str, str]) -> str:
    key = severity.strip().lower()
    if key in extra:
        return extra[key]
    return _SEVERITY_ALIASES.get(key, severity.upper())


def normalize_entry(entry: LogEntry, opts: NormalizeOptions) -> LogEntry:
    """Return a new LogEntry with normalised fields."""
    severity = entry.severity
    message = entry.message
    source = entry.source

    if opts.severity:
        severity = _normalize_severity(severity, opts.extra_severity_map)

    if opts.strip_message:
        message = message.strip()

    if opts.uppercase_source and source:
        source = source.upper()

    return LogEntry(
        timestamp=entry.timestamp,
        severity=severity,
        message=message,
        source=source,
        raw=entry.raw,
        tags=dict(entry.tags),
    )


def normalize_entries(
    entries: Iterable[LogEntry],
    opts: NormalizeOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield normalised entries from *entries*."""
    if opts is None:
        opts = NormalizeOptions()
    for entry in entries:
        yield normalize_entry(entry, opts)
