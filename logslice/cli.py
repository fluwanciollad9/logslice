"""Command-line interface for logslice.

Provides the `logslice` command that accepts a log file path along with
optional time-range and severity filters, then streams matching entries
to stdout (or a specified output file).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from logslice.formatter import FormatOptions
from logslice.slicer import slice_file
from logslice.writer import write_entries


# ---------------------------------------------------------------------------
# Timestamp parsing helper
# ---------------------------------------------------------------------------

_TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
]


def _parse_cli_timestamp(value: str) -> datetime:
    """Try several common formats and return a datetime, or raise ArgumentTypeError."""
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Cannot parse timestamp {value!r}. "
        "Expected formats: YYYY-MM-DD, YYYY-MM-DD HH:MM, YYYY-MM-DD HH:MM:SS, "
        "or ISO-8601 with T separator."
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="logslice",
        description="Fast log file slicer — filter by time range and severity.",
    )

    parser.add_argument(
        "file",
        metavar="FILE",
        help="Path to the log file to slice.",
    )
    parser.add_argument(
        "--start",
        metavar="TIMESTAMP",
        type=_parse_cli_timestamp,
        default=None,
        help="Include entries at or after this timestamp (e.g. '2024-01-15 08:00:00').",
    )
    parser.add_argument(
        "--end",
        metavar="TIMESTAMP",
        type=_parse_cli_timestamp,
        default=None,
        help="Include entries at or before this timestamp.",
    )
    parser.add_argument(
        "--severity",
        metavar="LEVEL",
        default=None,
        help="Minimum severity level to include (e.g. WARNING, ERROR).",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        default=False,
        help="Colorize severity labels in output (requires ANSI terminal).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="fmt",
        help="Output format: 'text' (default) or 'json'.",
    )

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    """Parse arguments, run the slice, and write results.

    Returns the process exit code (0 on success, non-zero on error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    fmt_options = FormatOptions(
        use_color=args.color,
        output_format=args.fmt,
    )

    try:
        entries = slice_file(
            path=args.file,
            start=args.start,
            end=args.end,
            min_severity=args.severity,
        )
        count = write_entries(
            entries=entries,
            fmt_options=fmt_options,
            output_path=args.output,
        )
    except FileNotFoundError:
        print(f"logslice: error: file not found: {args.file}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"logslice: error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        print(f"logslice: wrote {count} entr{'y' if count == 1 else 'ies'} to {args.output}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
