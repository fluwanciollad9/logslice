"""Split a log stream into per-severity or per-tag output files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, Optional

from logslice.parser import LogEntry


@dataclass
class SplitOptions:
    """Options controlling how entries are split into output files."""

    output_dir: str = "."
    by: str = "severity"  # 'severity' or 'tag'
    tag_key: Optional[str] = None  # required when by='tag'
    filename_template: str = "{key}.log"
    create_dirs: bool = True

    def __post_init__(self) -> None:
        if self.by not in ("severity", "tag"):
            raise ValueError("by must be 'severity' or 'tag'")
        if self.by == "tag" and not self.tag_key:
            raise ValueError("tag_key is required when by='tag'")


def _entry_key(entry: LogEntry, opts: SplitOptions) -> str:
    """Return the bucket key for a given entry."""
    if opts.by == "severity":
        return (entry.severity or "UNKNOWN").upper()
    # by == 'tag'
    tags: Dict[str, str] = getattr(entry, "tags", {}) or {}
    return tags.get(opts.tag_key, "UNTAGGED")  # type: ignore[arg-type]


def split_entries(
    entries: Iterable[LogEntry],
    opts: Optional[SplitOptions] = None,
) -> Dict[str, int]:
    """Write entries to per-key files; return a dict of key -> count written."""
    if opts is None:
        opts = SplitOptions()

    if opts.create_dirs:
        os.makedirs(opts.output_dir, exist_ok=True)

    handles: Dict[str, object] = {}
    counts: Dict[str, int] = {}

    try:
        for entry in entries:
            key = _entry_key(entry, opts)
            if key not in handles:
                filename = opts.filename_template.format(key=key)
                path = os.path.join(opts.output_dir, filename)
                handles[key] = open(path, "a", encoding="utf-8")  # noqa: WPS515
                counts[key] = 0
            line = f"{entry.raw}\n" if entry.raw else f"{entry.timestamp} {entry.severity} {entry.message}\n"
            handles[key].write(line)  # type: ignore[union-attr]
            counts[key] += 1
    finally:
        for fh in handles.values():
            fh.close()  # type: ignore[union-attr]

    return counts


def iter_split_entries(
    entries: Iterable[LogEntry],
    opts: Optional[SplitOptions] = None,
) -> Iterator[tuple[str, LogEntry]]:
    """Yield (key, entry) pairs without writing to disk — useful for testing."""
    if opts is None:
        opts = SplitOptions()
    for entry in entries:
        yield _entry_key(entry, opts), entry
