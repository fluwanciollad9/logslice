"""Integration tests: flattener wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.flattener import FlattenOptions
from logslice.filter import FilterOptions


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=message,
    )


def _run(entries, flatten: FlattenOptions | None = None, filt: FilterOptions | None = None):
    opts = PipelineOptions(
        filter=filt or FilterOptions(),
        flatten=flatten or FlattenOptions(),
    )
    return list(run_pipeline(iter(entries), opts))


class TestPipelineFlattener:
    def test_flatten_disabled_by_default(self):
        entries = [_entry("line1\nline2")]
        result = _run(entries)
        assert len(result) == 1
        assert result[0].message == "line1\nline2"

    def test_flatten_expands_multiline(self):
        entries = [_entry("line1\nline2\nline3")]
        result = _run(entries, flatten=FlattenOptions(enabled=True))
        assert len(result) == 3
        assert result[0].message == "line1"
        assert result[2].message == "line3"

    def test_flatten_applied_before_filter(self):
        # Only entries whose message contains 'ERROR' should survive the filter.
        entries = [_entry("ok\nERROR: boom")]
        result = _run(
            entries,
            flatten=FlattenOptions(enabled=True),
            filt=FilterOptions(include_keywords=["ERROR"]),
        )
        assert len(result) == 1
        assert "ERROR" in result[0].message

    def test_flatten_with_tag_index_in_pipeline(self):
        entries = [_entry("a\nb")]
        result = _run(entries, flatten=FlattenOptions(enabled=True, tag_index=True))
        assert result[0].tags["line_index"] == "0"
        assert result[1].tags["line_index"] == "1"
