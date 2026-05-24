"""Pruner: remove log entries whose messages match discard patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Pattern

from logslice.parser import LogEntry


@dataclass
class PruneOptions:
    """Configuration for the pruner stage."""

    patterns: List[str] = field(default_factory=list)
    ignore_case: bool = True
    invert: bool = False  # when True, KEEP only entries that match

    def __post_init__(self) -> None:
        for p in self.patterns:
            if not p:
                raise ValueError("prune pattern must not be empty")
            try:
                re.compile(p)
            except re.error as exc:
                raise ValueError(f"invalid prune pattern {p!r}: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compiled(self) -> List[Pattern[str]]:
        flags = re.IGNORECASE if self.ignore_case else 0
        return [re.compile(p, flags) for p in self.patterns]


def _matches_any(message: str, compiled: List[Pattern[str]]) -> bool:
    return any(rx.search(message) for rx in compiled)


def prune_entries(
    entries: Iterable[LogEntry],
    options: Optional[PruneOptions] = None,
) -> Iterator[LogEntry]:
    """Yield entries that survive the prune rules.

    With *invert=False* (default) entries whose message matches ANY pattern
    are discarded.  With *invert=True* only entries that match at least one
    pattern are kept.
    """
    if options is None or not options.patterns:
        yield from entries
        return

    compiled = options._compiled()
    for entry in entries:
        matched = _matches_any(entry.message, compiled)
        if options.invert:
            if matched:
                yield entry
        else:
            if not matched:
                yield entry
