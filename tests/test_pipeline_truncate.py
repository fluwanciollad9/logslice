"""Integration tests verifying truncation is wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.truncator import TruncateOptions

_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(timestamp=_TS, severity=severity, message=message, raw=message)


class TestPipelineTruncation:
    def test_truncation_disabled_by_default(self):
        entries = [_entry("x" * 300)]
        opts = PipelineOptions()
        result = list(run_pipeline(entries, opts))
        assert len(result[0].message) == 300

    def test_truncation_enabled_shortens_messages(self):
        entries = [_entry("x" * 300)]
        opts = PipelineOptions(
            enable_truncate=True,
            truncate=TruncateOptions(max_length=50),
        )
        result = list(run_pipeline(entries, opts))
        assert len(result[0].message) == 50
        assert result[0].message.endswith("...")

    def test_truncation_preserves_short_messages(self):
        entries = [_entry("short")]
        opts = PipelineOptions(
            enable_truncate=True,
            truncate=TruncateOptions(max_length=100),
        )
        result = list(run_pipeline(entries, opts))
        assert result[0].message == "short"

    def test_truncation_applied_after_filtering(self):
        entries = [
            _entry("x" * 300, severity="DEBUG"),
            _entry("y" * 300, severity="ERROR"),
        ]
        from logslice.filter import FilterOptions
        opts = PipelineOptions(
            filter=FilterOptions(min_severity="ERROR"),
            enable_truncate=True,
            truncate=TruncateOptions(max_length=20),
        )
        result = list(run_pipeline(entries, opts))
        assert len(result) == 1
        assert result[0].severity == "ERROR"
        assert len(result[0].message) == 20

    def test_multiple_entries_all_truncated(self):
        entries = [_entry("a" * 500) for _ in range(10)]
        opts = PipelineOptions(
            enable_truncate=True,
            truncate=TruncateOptions(max_length=30),
        )
        result = list(run_pipeline(entries, opts))
        assert all(len(e.message) == 30 for e in result)

    def test_empty_input_yields_nothing(self):
        opts = PipelineOptions(enable_truncate=True)
        result = list(run_pipeline([], opts))
        assert result == []

    def test_truncation_does_not_mutate_original_entries(self):
        """Ensure run_pipeline yields new entries rather than modifying the originals."""
        original_message = "z" * 200
        entries = [_entry(original_message)]
        opts = PipelineOptions(
            enable_truncate=True,
            truncate=TruncateOptions(max_length=50),
        )
        result = list(run_pipeline(entries, opts))
        assert len(result[0].message) == 50
        # The original entry object must remain unchanged.
        assert entries[0].message == original_message
