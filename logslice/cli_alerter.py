"""CLI subcommand: alert — stream log entries and flag alert conditions."""
from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Optional

from logslice.alerter import AlertOptions, alert_entries
from logslice.parser import parse_line
from logslice.writer import write_entries


def add_alert_subparser(subparsers: _SubParsersAction) -> None:  # type: ignore[type-arg]
    p: ArgumentParser = subparsers.add_parser(
        "alert",
        help="Tag entries that breach a severity/count threshold within a time window.",
    )
    p.add_argument(
        "--severity",
        default="ERROR",
        metavar="LEVEL",
        help="Minimum severity to count towards threshold (default: ERROR).",
    )
    p.add_argument(
        "--threshold",
        type=int,
        default=3,
        metavar="N",
        help="Number of matching entries within the window to trigger an alert (default: 3).",
    )
    p.add_argument(
        "--window",
        type=float,
        default=60.0,
        dest="window_seconds",
        metavar="SECS",
        help="Sliding time window in seconds (default: 60).",
    )
    p.add_argument(
        "--tag",
        default="ALERT",
        dest="alert_tag",
        metavar="TAG",
        help="Extra field key added to alerted entries (default: ALERT).",
    )
    p.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Log file to read (default: stdin).",
    )
    p.set_defaults(func=_run_alert)


def _run_alert(args: Namespace) -> int:
    try:
        opts = AlertOptions(
            severity=args.severity,
            threshold=args.threshold,
            window_seconds=args.window_seconds,
            alert_tag=args.alert_tag,
        )
    except ValueError as exc:
        print(f"logslice alert: {exc}", file=sys.stderr)
        return 2

    stream: Optional[object] = None
    if args.file:
        try:
            stream = open(args.file, encoding="utf-8")  # noqa: WPS515
        except OSError as exc:
            print(f"logslice alert: {exc}", file=sys.stderr)
            return 1
    else:
        stream = sys.stdin

    try:
        lines = (line.rstrip("\n") for line in stream)  # type: ignore[union-attr]
        entries = (e for line in lines for e in [parse_line(line)] if e is not None)
        alerted = alert_entries(entries, opts)
        write_entries(alerted)
    finally:
        if args.file and stream is not sys.stdin:
            stream.close()  # type: ignore[union-attr]

    return 0
