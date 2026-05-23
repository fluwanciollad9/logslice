"""Pager: split a stream of log entries into fixed-size pages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator, Iterable, List

from logslice.parser import LogEntry


@dataclass
class PageOptions:
    page_size: int = 50
    page_number: int = 0  # 0-based; None means stream all pages

    def __post_init__(self) -> None:
        if self.page_size < 1:
            raise ValueError("page_size must be >= 1")
        if self.page_number < 0:
            raise ValueError("page_number must be >= 0")


@dataclass
class Page:
    number: int
    entries: List[LogEntry] = field(default_factory=list)

    def count(self) -> int:
        return len(self.entries)

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)


def page_entries(
    entries: Iterable[LogEntry],
    options: PageOptions | None = None,
) -> Generator[Page, None, None]:
    """Yield Page objects.  If options.page_number is set, yield only that page."""
    opts = options or PageOptions()
    current_page = Page(number=0)

    for entry in entries:
        current_page.append(entry)
        if current_page.count() == opts.page_size:
            if opts.page_number is None or current_page.number == opts.page_number:
                yield current_page
            if opts.page_number is not None and current_page.number == opts.page_number:
                return
            current_page = Page(number=current_page.number + 1)

    # Emit trailing partial page
    if current_page.count() > 0:
        if opts.page_number is None or current_page.number == opts.page_number:
            yield current_page


def iter_pages(
    entries: Iterable[LogEntry],
    options: PageOptions | None = None,
) -> Generator[Page, None, None]:
    """Alias for page_entries that streams all pages."""
    opts = options or PageOptions()
    yield from page_entries(entries, PageOptions(page_size=opts.page_size, page_number=opts.page_number))
