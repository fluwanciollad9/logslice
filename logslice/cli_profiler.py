"""CLI sub-command: profile — print a throughput/severity profile of a log slice."""
from __future__ import annotations

import argparse
import sys
from typing import TextIO

from logslice.profiler import ProfileOptions, profile_entries
from logslice.slicer import slice_file


def add_profile_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("profile", help="Profile severity distribution and throughput")
    p.add_argument("file", nargs="?", default="-", help="Log file (default: stdin)")
    p.add_argument(
        "--bucket",
        type=int,
        default=60,
        metavar="SECS",
        help="Bucket width in seconds for throughput chart (default: 60)",
    )
    p.add_argument(
        "--no-rate",
        dest="no_rate",
        action="store_true",
        help="Skip per-bucket throughput calculation",
    )
    p.set_defaults(func=_run_profile)


def _run_profile(args: argparse.Namespace, out: TextIO = sys.stdout) -> None:
    opts = ProfileOptions(
        bucket_seconds=args.bucket,
        include_rate=not args.no_rate,
    )
    source = args.file
    if source == "-":
        entries = slice_file(sys.stdin)  # type: ignore[arg-type]
    else:
        with open(source) as fh:
            entries = slice_file(fh)

    _, result = profile_entries(iter(entries), opts)

    out.write(f"Total entries : {result.total}\n")
    out.write("\nSeverity breakdown:\n")
    for sev, count in sorted(result.severity_counts.items()):
        pct = (count / result.total * 100) if result.total else 0
        out.write(f"  {sev:<12} {count:>6}  ({pct:.1f}%)\n")

    if opts.include_rate and result.bucket_counts:
        out.write("\nThroughput (entries per bucket):\n")
        peak = result.peak_bucket()
        for key in sorted(result.bucket_counts):
            cnt = result.bucket_counts[key]
            marker = "  <- peak" if key == peak else ""
            out.write(f"  {key}  {cnt:>6}{marker}\n")
