"""Export pipeline output to various formats (JSON, CSV, NDJSON)."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional

from logslice.parser import LogEntry

_VALID_FORMATS = {"text", "json", "ndjson", "csv"}
_CSV_FIELDS = ["timestamp", "severity", "message", "source", "tags"]


@dataclass
class ExportOptions:
    """Configuration for the exporter stage."""

    fmt: str = "text"
    # Include the raw original line when exporting structured formats.
    include_raw: bool = False
    # Pretty-print JSON output (only applies to 'json' format).
    indent: Optional[int] = None
    # Field names to include; empty list means all fields.
    fields: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.fmt not in _VALID_FORMATS:
            raise ValueError(
                f"Unknown export format {self.fmt!r}. "
                f"Valid formats: {sorted(_VALID_FORMATS)}"
            )
        if self.indent is not None and self.indent < 0:
            raise ValueError("indent must be a non-negative integer or None")
        unknown = set(self.fields) - set(_CSV_FIELDS)
        if unknown:
            raise ValueError(f"Unknown field(s): {sorted(unknown)}")


def _entry_to_dict(entry: LogEntry, include_raw: bool = False) -> dict:
    """Convert a LogEntry to a plain dictionary suitable for serialisation."""
    data: dict = {
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "severity": entry.severity,
        "message": entry.message,
        "source": entry.source,
        "tags": sorted(entry.tags) if entry.tags else [],
    }
    if include_raw:
        data["raw"] = entry.raw
    return data


def _filter_fields(data: dict, fields: List[str]) -> dict:
    """Return only the requested fields from *data*."""
    if not fields:
        return data
    return {k: v for k, v in data.items() if k in fields}


def export_entries(
    entries: Iterable[LogEntry],
    options: Optional[ExportOptions] = None,
) -> Iterator[str]:
    """Yield serialised lines for each entry according to *options*.

    For the ``json`` format the entire collection is buffered and emitted as a
    single JSON array.  All other formats stream one line at a time.
    """
    if options is None:
        options = ExportOptions()

    fmt = options.fmt

    if fmt == "text":
        # Passthrough — callers use the formatter for text output.
        for entry in entries:
            yield entry.raw or ""
        return

    if fmt == "ndjson":
        for entry in entries:
            data = _filter_fields(_entry_to_dict(entry, options.include_raw), options.fields)
            yield json.dumps(data, default=str)
        return

    if fmt == "json":
        rows = [
            _filter_fields(_entry_to_dict(e, options.include_raw), options.fields)
            for e in entries
        ]
        yield json.dumps(rows, indent=options.indent, default=str)
        return

    if fmt == "csv":
        active_fields = options.fields if options.fields else _CSV_FIELDS
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=active_fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        yield buf.getvalue().rstrip("\n")
        for entry in entries:
            buf = io.StringIO()
            row_writer = csv.DictWriter(
                buf,
                fieldnames=active_fields,
                extrasaction="ignore",
                lineterminator="\n",
            )
            data = _filter_fields(_entry_to_dict(entry, options.include_raw), options.fields)
            # Serialise list fields to a readable string for CSV.
            if "tags" in data and isinstance(data["tags"], list):
                data["tags"] = "|".join(data["tags"])
            row_writer.writerow(data)
            yield buf.getvalue().rstrip("\n")
        return
