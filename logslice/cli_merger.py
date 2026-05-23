"""CLI helpers for the merge sub-command."""
from __future__ import annotations

import argparse
import sys
from typing import List

from logslice.merger import MergeOptions, merge_entries
from logslice.parser import parse_line
from logslice.writer import write_entries


def add_merge_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the *merge* sub-command onto *subparsers*."""
    p = subparsers.add_parser(
        "merge",
        help="Merge two or more sorted log files into one ordered stream.",
    )
    p.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Input log files (use '-' for stdin).",
    )
    p.add_argument(
        "--key",
        default="timestamp",
        choices=["timestamp", "severity"],
        help="Field to merge on (default: timestamp).",
    )
    p.add_argument(
        "--order",
        default="asc",
        choices=["asc", "desc"],
        help="Sort order (default: asc).",
    )
    p.add_argument(
        "--tag-source",
        action="store_true",
        default=False,
        help="Annotate each entry with its source file index.",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    p.set_defaults(func=_run_merge)


def _open_stream(path: str):
    if path == "-":
        return sys.stdin
    return open(path, "r", encoding="utf-8", errors="replace")


def _run_merge(args: argparse.Namespace) -> int:
    opts = MergeOptions(
        key=args.key,
        order=args.order,
        tag_source=args.tag_source,
    )

    handles = [_open_stream(p) for p in args.files]
    try:
        streams = [
            (parse_line(line) for line in fh if line.strip())
            for fh in handles
        ]
        # Filter out None (unparseable) entries from each stream
        valid_streams = [
            (e for e in s if e is not None)
            for s in streams
        ]
        merged = merge_entries(valid_streams, opts)  # type: ignore[arg-type]
        count = write_entries(merged, output=args.output)
    finally:
        for fh in handles:
            if fh is not sys.stdin:
                fh.close()

    return 0
