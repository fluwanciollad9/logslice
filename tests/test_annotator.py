"""Tests for logslice.annotator."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.annotator import AnnotateOptions, annotate_entries


def _entry(msg: str = "hello", sev: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=sev,
        message=msg,
        raw=f"2024-01-01T00:00:00Z {sev} {msg}",
        tags={},
    )


class TestAnnotateOptions:
    def test_defaults(self):
        opts = AnnotateOptions()
        assert opts.enabled is False
        assert opts.prefix == "#"
        assert opts.start == 1
        assert opts.step == 1
        assert opts.tag_key == "lineno"

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="step"):
            AnnotateOptions(step=0)

    def test_negative_step_raises(self):
        with pytest.raises(ValueError, match="step"):
            AnnotateOptions(step=-1)

    def test_negative_start_raises(self):
        with pytest.raises(ValueError, match="start"):
            AnnotateOptions(start=-1)

    def test_empty_tag_key_raises(self):
        with pytest.raises(ValueError, match="tag_key"):
            AnnotateOptions(tag_key="")


class TestAnnotateEntries:
    def test_disabled_passes_through_unchanged(self):
        entries = [_entry("a"), _entry("b")]
        result = list(annotate_entries(entries, AnnotateOptions(enabled=False)))
        assert [e.message for e in result] == ["a", "b"]

    def test_none_options_passes_through(self):
        entries = [_entry("x")]
        result = list(annotate_entries(entries, None))
        assert result[0].message == "x"

    def test_enabled_prepends_prefix_and_counter(self):
        entries = [_entry("msg1"), _entry("msg2"), _entry("msg3")]
        opts = AnnotateOptions(enabled=True, prefix="#", start=1)
        result = list(annotate_entries(entries, opts))
        assert result[0].message == "#1 msg1"
        assert result[1].message == "#2 msg2"
        assert result[2].message == "#3 msg3"

    def test_counter_stored_in_tags(self):
        entries = [_entry("a"), _entry("b")]
        opts = AnnotateOptions(enabled=True)
        result = list(annotate_entries(entries, opts))
        assert result[0].tags["lineno"] == "1"
        assert result[1].tags["lineno"] == "2"

    def test_custom_start_and_step(self):
        entries = [_entry("a"), _entry("b"), _entry("c")]
        opts = AnnotateOptions(enabled=True, start=10, step=5)
        result = list(annotate_entries(entries, opts))
        assert result[0].tags["lineno"] == "10"
        assert result[1].tags["lineno"] == "15"
        assert result[2].tags["lineno"] == "20"

    def test_empty_prefix_omits_prefix_in_message(self):
        entries = [_entry("hello")]
        opts = AnnotateOptions(enabled=True, prefix="", start=1)
        result = list(annotate_entries(entries, opts))
        assert result[0].message == "hello"
        assert result[0].tags["lineno"] == "1"

    def test_custom_tag_key(self):
        entries = [_entry("x")]
        opts = AnnotateOptions(enabled=True, tag_key="seq")
        result = list(annotate_entries(entries, opts))
        assert "seq" in result[0].tags
        assert "lineno" not in result[0].tags

    def test_existing_tags_preserved(self):
        entry = _entry("msg")
        entry = LogEntry(
            timestamp=entry.timestamp,
            severity=entry.severity,
            message=entry.message,
            raw=entry.raw,
            tags={"env": "prod"},
        )
        opts = AnnotateOptions(enabled=True)
        result = list(annotate_entries([entry], opts))
        assert result[0].tags["env"] == "prod"
        assert result[0].tags["lineno"] == "1"

    def test_original_entries_not_mutated(self):
        entry = _entry("original")
        opts = AnnotateOptions(enabled=True)
        result = list(annotate_entries([entry], opts))
        assert entry.message == "original"
        assert result[0].message == "#1 original"
