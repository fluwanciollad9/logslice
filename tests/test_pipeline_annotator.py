"""Integration tests: annotator wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.annotator import AnnotateOptions, annotate_entries
from logslice.filter import FilterOptions, filter_entries


def _entry(msg: str, sev: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=sev,
        message=msg,
        raw=f"2024-01-01 {sev} {msg}",
        tags={},
    )


def _run(
    entries,
    *,
    min_severity: str | None = None,
    annotate: bool = False,
    prefix: str = "#",
    start: int = 1,
):
    fopts = FilterOptions(min_severity=min_severity)
    aopts = AnnotateOptions(enabled=annotate, prefix=prefix, start=start)
    filtered = filter_entries(entries, fopts)
    annotated = list(annotate_entries(filtered, aopts))
    return annotated


class TestPipelineAnnotator:
    def test_annotation_disabled_by_default(self):
        entries = [_entry("a"), _entry("b")]
        result = _run(entries)
        assert result[0].message == "a"
        assert result[1].message == "b"

    def test_annotation_numbers_filtered_output(self):
        entries = [
            _entry("debug msg", "DEBUG"),
            _entry("info msg", "INFO"),
            _entry("error msg", "ERROR"),
        ]
        result = _run(entries, min_severity="INFO", annotate=True)
        # DEBUG entry filtered out, so only 2 entries annotated
        assert len(result) == 2
        assert result[0].message == "#1 info msg"
        assert result[1].message == "#2 error msg"

    def test_line_numbers_reflect_post_filter_position(self):
        entries = [_entry("a"), _entry("b"), _entry("c")]
        result = _run(entries, annotate=True, start=0)
        assert result[0].tags["lineno"] == "0"
        assert result[1].tags["lineno"] == "1"
        assert result[2].tags["lineno"] == "2"

    def test_custom_prefix_applied(self):
        entries = [_entry("hello")]
        result = _run(entries, annotate=True, prefix=">>")
        assert result[0].message == ">>1 hello"
