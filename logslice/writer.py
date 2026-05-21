"""Write formatted log output to files or stdout."""

import sys
from pathlib import Path
from typing import Iterable, Optional, TextIO

from logslice.formatter import FormatOptions, format_entry
from logslice.parser import LogEntry


def write_entries(
    entries: Iterable[LogEntry],
    destination: Optional[str] = None,
    options: Optional[FormatOptions] = None,
    source: str = "",
) -> int:
    """Write *entries* to *destination* (file path) or stdout.

    Returns the number of entries written.
    """
    if options is None:
        options = FormatOptions()

    handle: TextIO
    close_after = False

    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w", encoding="utf-8")
        close_after = True
    else:
        handle = sys.stdout

    count = 0
    try:
        for entry in entries:
            line = format_entry(entry, options, source)
            handle.write(line + "\n")
            count += 1
    finally:
        if close_after:
            handle.close()

    return count


def write_lines(
    lines: Iterable[str],
    destination: Optional[str] = None,
) -> int:
    """Write raw *lines* to *destination* or stdout without reformatting."""
    handle: TextIO
    close_after = False

    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w", encoding="utf-8")
        close_after = True
    else:
        handle = sys.stdout

    count = 0
    try:
        for line in lines:
            handle.write(line if line.endswith("\n") else line + "\n")
            count += 1
    finally:
        if close_after:
            handle.close()

    return count
