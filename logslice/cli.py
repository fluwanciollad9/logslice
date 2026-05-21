"""Command-line interface for logslice."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Optional

from logslice.filter import FilterOptions
from logslice.formatter import FormatOptions
from logslice.slicer import slice_file
from logslice.writer import write_entries


def _parse_cli_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp from the CLI, attaching UTC if no tz given."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise argparse.ArgumentTypeError(f"Cannot parse timestamp: {value!r}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logslice",
        description="Slice log files by time range, severity, and keywords.",
    )
    p.add_argument("file", nargs="?", help="Log file to read (default: stdin)")
    p.add_argument("--from", dest="from_ts", type=_parse_cli_timestamp, metavar="TS",
                   help="Start of time range (inclusive)")
    p.add_argument("--to", dest="to_ts", type=_parse_cli_timestamp, metavar="TS",
                   help="End of time range (inclusive)")
    p.add_argument("--severity", "-s", metavar="LEVEL",
                   help="Minimum severity level (e.g. WARNING)")
    p.add_argument("--include", "-i", action="append", default=[], metavar="KW",
                   help="Only show entries containing keyword (repeatable)")
    p.add_argument("--exclude", "-e", action="append", default=[], metavar="KW",
                   help="Hide entries containing keyword (repeatable)")
    p.add_argument("--include-pattern", metavar="RE",
                   help="Only show entries matching regex")
    p.add_argument("--exclude-pattern", metavar="RE",
                   help="Hide entries matching regex")
    p.add_argument("--case-sensitive", action="store_true",
                   help="Make keyword/pattern matching case-sensitive")
    p.add_argument("--output", "-o", metavar="FILE",
                   help="Write output to FILE instead of stdout")
    p.add_argument("--format", dest="fmt", choices=("text", "json"), default="text",
                   help="Output format (default: text)")
    p.add_argument("--color", action="store_true", help="Colorize text output")
    p.add_argument("--stats", action="store_true", help="Print slice statistics to stderr")
    return p


def main(argv: Optional[list[str]] = None) -> int:  # noqa: D401
    parser = build_parser()
    args = parser.parse_args(argv)

    filter_opts = FilterOptions(
        include_keywords=args.include,
        exclude_keywords=args.exclude,
        include_pattern=args.include_pattern,
        exclude_pattern=args.exclude_pattern,
        case_sensitive=args.case_sensitive,
    )
    fmt_opts = FormatOptions(fmt=args.fmt, colorize=args.color)

    entries, stats = slice_file(
        path=args.file,
        from_ts=args.from_ts,
        to_ts=args.to_ts,
        min_severity=args.severity,
        return_stats=args.stats,
        filter_opts=filter_opts,
    )

    count = write_entries(entries, output=args.output, fmt_opts=fmt_opts)

    if args.stats and stats is not None:
        print(
            f"lines={stats.total_lines} matched={stats.matched_lines} "
            f"skipped={stats.skipped_lines} unparseable={stats.unparseable_lines}",
            file=sys.stderr,
        )

    return 0 if count >= 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
