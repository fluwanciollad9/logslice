"""Entry count limiter — cap the number of entries yielded from a stream."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry


@dataclass
class LimitOptions:
    """Options controlling how many entries are passed through."""

    head: int | None = None  # keep first N entries
    tail: int | None = None  # keep last N entries

    def __post_init__(self) -> None:
        if self.head is not None and self.head < 0:
            raise ValueError("head must be >= 0")
        if self.tail is not None and self.tail < 0:
            raise ValueError("tail must be >= 0")
        if self.head is not None and self.tail is not None:
            raise ValueError("head and tail are mutually exclusive")


def limit_entries(
    entries: Iterable[LogEntry],
    opts: LimitOptions | None = None,
) -> Iterator[LogEntry]:
    """Yield entries according to *opts*.

    - ``head=N`` – yield only the first *N* entries.
    - ``tail=N`` – yield only the last *N* entries (buffers the stream).
    - Neither set – yield all entries unchanged.
    """
    if opts is None or (opts.head is None and opts.tail is None):
        yield from entries
        return

    if opts.head is not None:
        count = 0
        for entry in entries:
            if count >= opts.head:
                break
            yield entry
            count += 1
        return

    # tail mode — must buffer
    assert opts.tail is not None
    if opts.tail == 0:
        return
    buf: list[LogEntry] = []
    for entry in entries:
        buf.append(entry)
        if len(buf) > opts.tail:
            buf.pop(0)
    yield from buf
