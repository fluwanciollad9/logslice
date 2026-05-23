"""CLI sub-command: page — paginate filtered log output."""
from __future__ import annotations

import argparse
import sys
from typing import List

from logslice.pager import PageOptions, page_entries
from logslice.slicer import slice_file
from logslice.filter import FilterOptions, filter_entries
from logslice.formatter import FormatOptions, format_entries
from logslice.writer import write_lines


def add_page_subparser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser("page", help="Paginate log output")
    p.add_argument("file", nargs="?", help="Log file (default: stdin)")
    p.add_argument("--page-size", type=int, default=50, metavar="N",
                   help="Entries per page (default: 50)")
    p.add_argument("--page", type=int, default=0, metavar="N",
                   help="0-based page number to display (default: 0)")
    p.add_argument("--all-pages", action="store_true",
                   help="Stream all pages (overrides --page)")
    p.add_argument("--min-severity", default=None)
    p.add_argument("--color", action="store_true", default=False)
    p.set_defaults(func=_run_page)


def _run_page(args: argparse.Namespace) -> int:
    stream = open(args.file) if args.file else sys.stdin  # noqa: WPS515
    try:
        entries, _ = slice_file(stream, stats=False)
        fopts = FilterOptions(min_severity=args.min_severity)
        filtered = filter_entries(entries, fopts)
        page_number = None if args.all_pages else args.page
        popts = PageOptions(page_size=args.page_size, page_number=page_number)
        fmt = FormatOptions(color=args.color)
        total_written = 0
        for page in page_entries(filtered, popts):
            lines = list(format_entries(page.entries, fmt))
            if not args.all_pages:
                print(f"--- Page {page.number} ({page.count()} entries) ---")
            total_written += write_lines(lines)
        return 0
    finally:
        if args.file:
            stream.close()
