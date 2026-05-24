"""Entry classifier: assigns a category label based on message patterns and severity."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Tuple
import re

from logslice.parser import LogEntry

_SEVERITY_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class ClassifyRule:
    category: str
    keyword: Optional[str] = None
    pattern: Optional[str] = None
    min_severity: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.category:
            raise ValueError("category must not be empty")
        if self.keyword is None and self.pattern is None and self.min_severity is None:
            raise ValueError("at least one condition (keyword, pattern, min_severity) is required")
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"invalid pattern {self.pattern!r}: {exc}") from exc
        if self.min_severity is not None and self.min_severity not in _SEVERITY_ORDER:
            raise ValueError(f"unknown severity {self.min_severity!r}")

    def matches(self, entry: LogEntry) -> bool:
        if self.keyword is not None and self.keyword.lower() not in entry.message.lower():
            return False
        if self.pattern is not None and not re.search(self.pattern, entry.message):
            return False
        if self.min_severity is not None:
            sev = entry.severity or "INFO"
            entry_rank = _SEVERITY_ORDER.index(sev) if sev in _SEVERITY_ORDER else 0
            min_rank = _SEVERITY_ORDER.index(self.min_severity)
            if entry_rank < min_rank:
                return False
        return True


@dataclass
class ClassifyOptions:
    rules: List[ClassifyRule] = field(default_factory=list)
    default_category: str = "uncategorized"
    tag_key: str = "category"

    def __post_init__(self) -> None:
        if not self.tag_key:
            raise ValueError("tag_key must not be empty")


def _classify_entry(entry: LogEntry, opts: ClassifyOptions) -> LogEntry:
    for rule in opts.rules:
        if rule.matches(entry):
            tags = dict(entry.tags or {})
            tags[opts.tag_key] = rule.category
            return LogEntry(
                timestamp=entry.timestamp,
                severity=entry.severity,
                message=entry.message,
                raw=entry.raw,
                tags=tags,
            )
    tags = dict(entry.tags or {})
    tags[opts.tag_key] = opts.default_category
    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=entry.message,
        raw=entry.raw,
        tags=tags,
    )


def classify_entries(
    entries: Iterable[LogEntry],
    opts: Optional[ClassifyOptions] = None,
) -> Iterator[LogEntry]:
    if opts is None or not opts.rules:
        yield from entries
        return
    for entry in entries:
        yield _classify_entry(entry, opts)
