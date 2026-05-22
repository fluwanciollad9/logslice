"""Tests for logslice.diffier."""
import pytest
from datetime import datetime, timezone
from logslice.diffier import DiffOptions, diff_entries
from logslice.parser import LogEntry


def _entry(message: str, severity: str = "INFO", source: str = "app") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        source=source,
        raw=f"INFO {message}",
        tags=[],
    )


class TestDiffOptions:
    def test_defaults(self):
        opts = DiffOptions()
        assert opts.field == "message"
        assert opts.enabled is False
        assert opts.include_unchanged is True

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="field must be one of"):
            DiffOptions(field="nonexistent")

    def test_empty_marker_changed_raises(self):
        with pytest.raises(ValueError, match="marker_changed"):
            DiffOptions(marker_changed="")

    def test_empty_marker_unchanged_raises(self):
        with pytest.raises(ValueError, match="marker_unchanged"):
            DiffOptions(marker_unchanged="")


class TestDiffEntries:
    def test_disabled_passes_through(self):
        entries = [_entry("hello"), _entry("world")]
        result = list(diff_entries(iter(entries), DiffOptions(enabled=False)))
        assert result == entries

    def test_none_options_passes_through(self):
        entries = [_entry("hello")]
        result = list(diff_entries(iter(entries), None))
        assert result == entries

    def test_first_entry_always_marked_changed(self):
        opts = DiffOptions(enabled=True)
        result = list(diff_entries(iter([_entry("hello")]), opts))
        assert any(t == "diff:~" for t in result[0].tags)

    def test_identical_messages_marked_unchanged(self):
        opts = DiffOptions(enabled=True)
        entries = [_entry("same"), _entry("same")]
        result = list(diff_entries(iter(entries), opts))
        assert any(t == "diff: " for t in result[1].tags)

    def test_different_messages_marked_changed(self):
        opts = DiffOptions(enabled=True)
        entries = [_entry("first"), _entry("second")]
        result = list(diff_entries(iter(entries), opts))
        assert any(t == "diff:~" for t in result[1].tags)

    def test_exclude_unchanged_suppresses_entries(self):
        opts = DiffOptions(enabled=True, include_unchanged=False)
        entries = [_entry("same"), _entry("same"), _entry("different")]
        result = list(diff_entries(iter(entries), opts))
        assert len(result) == 2
        assert result[1].message == "different"

    def test_diff_by_severity_field(self):
        opts = DiffOptions(enabled=True, field="severity")
        entries = [_entry("m", severity="INFO"), _entry("m", severity="INFO")]
        result = list(diff_entries(iter(entries), opts))
        assert any(t == "diff: " for t in result[1].tags)

    def test_stale_diff_tag_replaced(self):
        opts = DiffOptions(enabled=True)
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            severity="INFO",
            message="hello",
            source="app",
            raw="INFO hello",
            tags=["diff: ", "other"],
        )
        result = list(diff_entries(iter([entry]), opts))
        diff_tags = [t for t in result[0].tags if t.startswith("diff:")]
        assert len(diff_tags) == 1
        assert diff_tags[0] == "diff:~"
        assert "other" in result[0].tags
