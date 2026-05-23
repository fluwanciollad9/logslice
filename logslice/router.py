"""Route log entries to named output channels based on rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Generator, Iterable, List, Optional, Tuple

from logslice.parser import LogEntry


@dataclass
class RouteRule:
    """A single routing rule: entries matching the condition go to *channel*."""

    channel: str
    severity: Optional[str] = None
    keyword: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.channel:
            raise ValueError("channel must not be empty")
        if self.severity is None and self.keyword is None:
            raise ValueError("at least one of severity or keyword must be set")

    def matches(self, entry: LogEntry) -> bool:
        if self.severity is not None:
            if (entry.severity or "").upper() != self.severity.upper():
                return False
        if self.keyword is not None:
            if self.keyword.lower() not in (entry.message or "").lower():
                return False
        return True


@dataclass
class RouterOptions:
    rules: List[RouteRule] = field(default_factory=list)
    default_channel: str = "default"
    emit_unmatched: bool = True

    def __post_init__(self) -> None:
        if not self.default_channel:
            raise ValueError("default_channel must not be empty")


def route_entries(
    entries: Iterable[LogEntry],
    options: Optional[RouterOptions] = None,
) -> Generator[Tuple[str, LogEntry], None, None]:
    """Yield (channel, entry) pairs according to *options*.

    The first matching rule wins.  Unmatched entries go to
    ``options.default_channel`` when *emit_unmatched* is True.
    """
    if options is None:
        options = RouterOptions()

    for entry in entries:
        matched_channel: Optional[str] = None
        for rule in options.rules:
            if rule.matches(entry):
                matched_channel = rule.channel
                break
        if matched_channel is not None:
            yield matched_channel, entry
        elif options.emit_unmatched:
            yield options.default_channel, entry


def route_to_dict(
    entries: Iterable[LogEntry],
    options: Optional[RouterOptions] = None,
) -> Dict[str, List[LogEntry]]:
    """Collect routed entries into a channel-keyed dictionary."""
    result: Dict[str, List[LogEntry]] = {}
    for channel, entry in route_entries(entries, options):
        result.setdefault(channel, []).append(entry)
    return result
