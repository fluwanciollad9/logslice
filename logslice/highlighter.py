"""Keyword highlighting for log entry messages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry

_ANSI_RESET = "\033[0m"
_ANSI_BOLD_YELLOW = "\033[1;33m"
_ANSI_BOLD_RED = "\033[1;31m"
_ANSI_BOLD_CYAN = "\033[1;36m"

_LEVEL_COLORS = {
    "error": _ANSI_BOLD_RED,
    "warning": _ANSI_BOLD_YELLOW,
    "info": _ANSI_BOLD_CYAN,
}


@dataclass
class HighlightOptions:
    keywords: list[str] = field(default_factory=list)
    color: bool = True
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.keywords, list):
            raise TypeError("keywords must be a list")


def _highlight_keywords(text: str, keywords: list[str], color: bool, case_sensitive: bool) -> str:
    """Wrap each keyword occurrence in the text with ANSI codes."""
    if not keywords or not color:
        return text

    for kw in keywords:
        if not kw:
            continue
        search = kw if case_sensitive else kw.lower()
        compare = text if case_sensitive else text.lower()
        result = []
        pos = 0
        while True:
            idx = compare.find(search, pos)
            if idx == -1:
                result.append(text[pos:])
                break
            result.append(text[pos:idx])
            result.append(f"{_ANSI_BOLD_YELLOW}{text[idx:idx + len(kw)]}{_ANSI_RESET}")
            pos = idx + len(kw)
        text = "".join(result)
        compare = text if case_sensitive else text.lower()
    return text


def highlight_entry(entry: LogEntry, opts: HighlightOptions) -> LogEntry:
    """Return a new LogEntry with keywords highlighted in the message."""
    highlighted = _highlight_keywords(
        entry.message, opts.keywords, opts.color, opts.case_sensitive
    )
    return LogEntry(
        timestamp=entry.timestamp,
        severity=entry.severity,
        message=highlighted,
        raw=entry.raw,
    )


def highlight_entries(
    entries: Iterable[LogEntry], opts: HighlightOptions
) -> Iterator[LogEntry]:
    """Yield entries with keywords highlighted in their messages."""
    for entry in entries:
        yield highlight_entry(entry, opts)
