"""Keyword and regex filtering for log entries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

from logslice.parser import LogEntry


@dataclass
class FilterOptions:
    """Options controlling keyword/regex filtering of log entries."""

    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._include_re: Optional[re.Pattern[str]] = (
            re.compile(self.include_pattern, flags) if self.include_pattern else None
        )
        self._exclude_re: Optional[re.Pattern[str]] = (
            re.compile(self.exclude_pattern, flags) if self.exclude_pattern else None
        )


def _matches(text: str, opts: FilterOptions) -> bool:
    """Return True if *text* passes all active filter criteria."""
    compare = text if opts.case_sensitive else text.lower()

    for kw in opts.include_keywords:
        needle = kw if opts.case_sensitive else kw.lower()
        if needle not in compare:
            return False

    for kw in opts.exclude_keywords:
        needle = kw if opts.case_sensitive else kw.lower()
        if needle in compare:
            return False

    if opts._include_re and not opts._include_re.search(text):
        return False

    if opts._exclude_re and opts._exclude_re.search(text):
        return False

    return True


def filter_entries(
    entries: Iterable[LogEntry],
    opts: FilterOptions,
) -> Iterator[LogEntry]:
    """Yield only entries whose message satisfies *opts*."""
    for entry in entries:
        if _matches(entry.message, opts):
            yield entry
