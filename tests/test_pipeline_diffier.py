"""Integration tests: diffier wired through the pipeline."""
from datetime import datetime, timezone
from typing import List

from logslice.diffier import DiffOptions, diff_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        source="svc",
        raw=f"{severity} {message}",
        tags=[],
    )


def _run(
    entries: List[LogEntry],
    diff_opts: DiffOptions,
    filter_opts: FilterOptions,
) -> List[LogEntry]:
    """Run entries through the filter then diffier pipeline and return results."""
    filtered = filter_entries(iter(entries), filter_opts)
    diffed = diff_entries(filtered, diff_opts)
    return list(diffed)


class TestPipelineDiffier:
    def test_diff_disabled_by_default(self):
        entries = [_entry("a"), _entry("b")]
        result = _run(entries, DiffOptions(), FilterOptions())
        assert all(not any(t.startswith("diff:") for t in e.tags) for e in result)

    def test_diff_tags_appear_after_filter(self):
        entries = [_entry("keep", "ERROR"), _entry("keep", "ERROR")]
        opts = DiffOptions(enabled=True)
        f_opts = FilterOptions(min_severity="ERROR")
        result = _run(entries, opts, f_opts)
        assert len(result) == 2
        assert any(t.startswith("diff:") for t in result[0].tags)
        assert any(t.startswith("diff:") for t in result[1].tags)

    def test_filter_reduces_entries_before_diff(self):
        entries = [
            _entry("debug msg", "DEBUG"),
            _entry("error msg", "ERROR"),
            _entry("error msg", "ERROR"),
        ]
        opts = DiffOptions(enabled=True, include_unchanged=False)
        f_opts = FilterOptions(min_severity="ERROR")
        result = _run(entries, opts, f_opts)
        # Only first ERROR passes (second is unchanged and suppressed)
        assert len(result) == 1
        assert result[0].message == "error msg"

    def test_empty_input_returns_empty(self):
        """Pipeline should handle an empty entry list without errors."""
        result = _run([], DiffOptions(enabled=True), FilterOptions())
        assert result == []
