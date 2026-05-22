"""Masker: redact sensitive patterns from log entry messages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Generator, Iterable, List, Optional

from logslice.parser import LogEntry

_BUILTIN_PATTERNS: dict[str, str] = {
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "jwt": r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
    "uuid": r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
}


@dataclass
class MaskOptions:
    """Options controlling which patterns are redacted."""

    builtins: List[str] = field(default_factory=list)
    custom_patterns: List[str] = field(default_factory=list)
    replacement: str = "[REDACTED]"

    def __post_init__(self) -> None:
        unknown = set(self.builtins) - _BUILTIN_PATTERNS.keys()
        if unknown:
            raise ValueError(f"Unknown builtin pattern(s): {sorted(unknown)}")
        for pat in self.custom_patterns:
            try:
                re.compile(pat)
            except re.error as exc:
                raise ValueError(f"Invalid custom pattern {pat!r}: {exc}") from exc

    # ------------------------------------------------------------------
    def _compiled(self) -> List[re.Pattern[str]]:
        patterns = [_BUILTIN_PATTERNS[name] for name in self.builtins]
        patterns += self.custom_patterns
        return [re.compile(p) for p in patterns]


def _mask_message(message: str, compiled: List[re.Pattern[str]], replacement: str) -> str:
    for pattern in compiled:
        message = pattern.sub(replacement, message)
    return message


def mask_entry(entry: LogEntry, opts: MaskOptions) -> LogEntry:
    """Return a new LogEntry with sensitive data redacted from the message."""
    compiled = opts._compiled()
    if not compiled:
        return entry
    new_message = _mask_message(entry.message, compiled, opts.replacement)
    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=new_message,
        raw=entry.raw,
        tags=entry.tags,
    )


def mask_entries(
    entries: Iterable[LogEntry],
    opts: Optional[MaskOptions] = None,
) -> Generator[LogEntry, None, None]:
    """Yield entries with sensitive fields masked according to *opts*."""
    if opts is None or (not opts.builtins and not opts.custom_patterns):
        yield from entries
        return
    compiled = opts._compiled()
    for entry in entries:
        yield LogEntry(
            timestamp=entry.timestamp,
            severity=entry.severity,
            message=_mask_message(entry.message, compiled, opts.replacement),
            raw=entry.raw,
            tags=entry.tags,
        )
