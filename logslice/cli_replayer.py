"""CLI sub-command: replay — stream a log file honouring original timing."""
from __future__ import annotations

import argparse
import sys
from typing import TextIO

from logslice.replayer import ReplayOptions, replay_entries
from logslice.slicer import slice_file
from logslice.formatter import FormatOptions, format_entries
from logslice.writer import write_lines


def add_replay_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "replay",
        help="Re-emit log entries with delays that mirror original timestamps.",
    )
    p.add_argument("file", nargs="?", default="-", help="Log file (default: stdin)")
    p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed multiplier (default: 1.0)",
    )
    p.add_argument(
        "--max-delay",
        type=float,
        default=5.0,
        dest="max_delay",
        help="Maximum inter-event sleep in seconds (default: 5.0)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Disable real-time delays; emit entries immediately.",
    )
    p.set_defaults(func=_run_replay)


def _run_replay(args: argparse.Namespace, out: TextIO = sys.stdout) -> int:
    try:
        opts = ReplayOptions(
            speed=args.speed,
            max_delay=args.max_delay,
            real_time=not args.dry_run,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stream = sys.stdin if args.file == "-" else open(args.file)
    try:
        entries = slice_file(stream)
        replayed = replay_entries(entries, opts)
        fmt = FormatOptions()
        lines = (line for entry in replayed for line in [format_entries([entry], fmt).__next__()]) # type: ignore[attr-defined]
        return write_lines(
            (fmt_entry for entry in replay_entries(slice_file(stream if args.file == "-" else open(args.file)), opts)
             for fmt_entry in [entry.raw]),
            out,
        )
    finally:
        if args.file != "-":
            stream.close()
