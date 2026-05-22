"""Tag log entries with user-defined labels based on keyword or severity rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class TagRule:
    """A single tagging rule: apply *tag* when *keyword* appears in the message
    or when *severity* matches the entry's severity (case-insensitive)."""

    tag: str
    keyword: str | None = None
    severity: str | None = None

    def __post_init__(self) -> None:
        if not self.tag or not self.tag.strip():
            raise ValueError("tag must be a non-empty string")
        if self.keyword is None and self.severity is None:
            raise ValueError("at least one of keyword or severity must be set")


@dataclass
class TaggerOptions:
    """Options controlling how entries are tagged."""

    rules: list[TagRule] = field(default_factory=list)
    multi_tag: bool = True  # allow multiple tags per entry


def _apply_rules(entry: LogEntry, rules: list[TagRule], multi_tag: bool) -> LogEntry:
    """Return a copy of *entry* with its tags field populated."""
    tags: list[str] = []
    for rule in rules:
        matched = False
        if rule.keyword and rule.keyword.lower() in entry.message.lower():
            matched = True
        if rule.severity and rule.severity.lower() == (entry.severity or "").lower():
            matched = True
        if matched:
            tags.append(rule.tag)
            if not multi_tag:
                break
    # LogEntry is a dataclass — return a shallow copy with tags replaced
    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=entry.message,
        raw=entry.raw,
        tags=tags,
    )


def tag_entries(
    entries: Iterable[LogEntry],
    options: TaggerOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries annotated according to *options*."""
    if options is None:
        options = TaggerOptions()
    for entry in entries:
        yield _apply_rules(entry, options.rules, options.multi_tag)
