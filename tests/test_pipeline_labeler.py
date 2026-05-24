"""Integration tests for labeler inside the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.labeler import LabelOptions
from logslice.filter import FilterOptions
from logslice.pipeline import PipelineOptions, run_pipeline


def _entry(severity: str = "INFO", message: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=f"2024-01-01T00:00:00Z {severity} {message}",
        tags={},
    )


def _run(entries, label_opts=None, filter_opts=None):
    opts = PipelineOptions(
        filter=filter_opts or FilterOptions(),
        label=label_opts,
    )
    return list(run_pipeline(iter(entries), opts))


class TestPipelineLabeler:
    def test_labeling_disabled_by_default_passes_all(self):
        entries = [_entry(), _entry()]
        result = _run(entries)
        assert len(result) == 2

    def test_labels_applied_to_all_filtered_entries(self):
        entries = [_entry("INFO"), _entry("ERROR")]
        result = _run(
            entries,
            label_opts=LabelOptions(labels={"env": "staging"}),
        )
        assert all(e.tags.get("env") == "staging" for e in result)

    def test_only_filtered_entries_are_labeled(self):
        entries = [_entry("INFO"), _entry("DEBUG"), _entry("ERROR")]
        result = _run(
            entries,
            label_opts=LabelOptions(labels={"tagged": "yes"}),
            filter_opts=FilterOptions(min_severity="ERROR"),
        )
        assert len(result) == 1
        assert result[0].tags["tagged"] == "yes"
