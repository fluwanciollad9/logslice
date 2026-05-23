"""CLI sub-command: route — split a log stream into per-channel files."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from logslice.router import RouteRule, RouterOptions, route_entries
from logslice.slicer import slice_file
from logslice.formatter import FormatOptions, format_entry


def add_route_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "route",
        help="Route log entries to named channels based on severity/keyword rules.",
    )
    p.add_argument("file", nargs="?", help="Input log file (default: stdin)")
    p.add_argument(
        "--rule",
        dest="rules",
        metavar="CHANNEL:SEVERITY_OR_KEYWORD",
        action="append",
        default=[],
        help="Routing rule in the form channel:value (repeatable). "
             "Prefix value with 's:' for severity, 'k:' for keyword.",
    )
    p.add_argument(
        "--default-channel",
        default="default",
        help="Channel name for unmatched entries (default: 'default').",
    )
    p.add_argument(
        "--drop-unmatched",
        action="store_true",
        default=False,
        help="Discard entries that match no rule.",
    )
    p.set_defaults(func=_run_route)


def _parse_rules(raw_rules: List[str]) -> List[RouteRule]:
    rules: List[RouteRule] = []
    for raw in raw_rules:
        if ":" not in raw:
            raise argparse.ArgumentTypeError(
                f"Invalid rule {raw!r}: expected 'channel:s:SEVERITY' or 'channel:k:KEYWORD'"
            )
        channel, _, rest = raw.partition(":")
        if rest.startswith("s:"):
            rules.append(RouteRule(channel=channel, severity=rest[2:]))
        elif rest.startswith("k:"):
            rules.append(RouteRule(channel=channel, keyword=rest[2:]))
        else:
            # Treat bare value as a keyword for convenience
            rules.append(RouteRule(channel=channel, keyword=rest))
    return rules


def _run_route(args: argparse.Namespace) -> None:
    rules = _parse_rules(args.rules)
    opts = RouterOptions(
        rules=rules,
        default_channel=args.default_channel,
        emit_unmatched=not args.drop_unmatched,
    )
    fmt = FormatOptions()

    stream = open(args.file) if args.file else sys.stdin  # type: ignore[assignment]
    try:
        entries = slice_file(stream)  # type: ignore[arg-type]
        for channel, entry in route_entries(entries, opts):
            line = format_entry(entry, fmt)
            sys.stdout.write(f"[{channel}] {line}\n")
    finally:
        if args.file:
            stream.close()  # type: ignore[union-attr]
