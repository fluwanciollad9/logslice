"""Output formatters for log entries."""

from dataclasses import dataclass
from typing import List, Optional
from logslice.parser import LogEntry


@dataclass
class FormatOptions:
    """Options controlling output format."""
    fmt: str = "text"          # 'text', 'json', 'csv'
    show_source: bool = False   # include source filename
    color: bool = False         # ANSI color for severity


_SEVERITY_COLORS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"


def _colorize(severity: str, text: str) -> str:
    color = _SEVERITY_COLORS.get(severity.upper(), "")
    return f"{color}{text}{_RESET}" if color else text


def format_entry(entry: LogEntry, options: Optional[FormatOptions] = None, source: str = "") -> str:
    """Format a single LogEntry according to *options*."""
    if options is None:
        options = FormatOptions()

    ts = entry.timestamp.isoformat(sep=" ") if entry.timestamp else ""
    severity = entry.severity or ""
    message = entry.message or ""

    if options.fmt == "json":
        import json
        obj = {"timestamp": ts, "severity": severity, "message": message}
        if options.show_source and source:
            obj["source"] = source
        return json.dumps(obj)

    if options.fmt == "csv":
        import csv, io
        buf = io.StringIO()
        fields = [ts, severity, message]
        if options.show_source and source:
            fields.insert(0, source)
        csv.writer(buf).writerow(fields)
        return buf.getvalue().rstrip("\r\n")

    # default: text
    sev_str = _colorize(severity, severity) if options.color else severity
    parts = []
    if options.show_source and source:
        parts.append(f"[{source}]")
    parts.append(f"{ts} {sev_str} {message}")
    return " ".join(parts)


def format_entries(
    entries: List[LogEntry],
    options: Optional[FormatOptions] = None,
    source: str = "",
) -> List[str]:
    """Format a list of LogEntry objects."""
    return [format_entry(e, options, source) for e in entries]
