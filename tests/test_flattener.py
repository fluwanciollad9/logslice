"""Tests for logslice.flattener."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.flattener import FlattenOptions, flatten_entry, flatten_entries


def _entry(message: str, tags: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity="INFO",
        message=message,
        raw=message,
        tags=tags,
    )


class TestFlattenOptions:
    def test_defaults(self):
        opts = FlattenOptions()
        assert opts.enabled is False
        assert opts.separator == "\n"
        assert opts.strip_lines is True
        assert opts.skip_empty is True
        assert opts.tag_index is False

    def test_empty_separator_raises(self):
        with pytest.raises(ValueError, match="separator"):
            FlattenOptions(separator="")


class TestFlattenEntry:
    def test_single_line_yields_one_entry(self):
        opts = FlattenOptions(enabled=True)
        results = list(flatten_entry(_entry("hello"), opts))
        assert len(results) == 1
        assert results[0].message == "hello"

    def test_multi_line_yields_multiple_entries(self):
        opts = FlattenOptions(enabled=True)
        results = list(flatten_entry(_entry("line1\nline2\nline3"), opts))
        assert len(results) == 3
        assert [r.message for r in results] == ["line1", "line2", "line3"]

    def test_strips_whitespace_when_enabled(self):
        opts = FlattenOptions(enabled=True, strip_lines=True)
        results = list(flatten_entry(_entry("  a  \n  b  "), opts))
        assert results[0].message == "a"
        assert results[1].message == "b"

    def test_no_strip_preserves_whitespace(self):
        opts = FlattenOptions(enabled=True, strip_lines=False)
        results = list(flatten_entry(_entry("  a  \n  b  "), opts))
        assert results[0].message == "  a  "

    def test_skip_empty_removes_blank_lines(self):
        opts = FlattenOptions(enabled=True, skip_empty=True)
        results = list(flatten_entry(_entry("a\n\nb"), opts))
        assert len(results) == 2

    def test_keep_empty_preserves_blank_lines(self):
        opts = FlattenOptions(enabled=True, skip_empty=False, strip_lines=False)
        results = list(flatten_entry(_entry("a\n\nb"), opts))
        assert len(results) == 3

    def test_tag_index_adds_line_index(self):
        opts = FlattenOptions(enabled=True, tag_index=True)
        results = list(flatten_entry(_entry("x\ny"), opts))
        assert results[0].tags["line_index"] == "0"
        assert results[1].tags["line_index"] == "1"

    def test_existing_tags_preserved(self):
        opts = FlattenOptions(enabled=True, tag_index=True)
        results = list(flatten_entry(_entry("a\nb", tags={"src": "test"}), opts))
        assert results[0].tags["src"] == "test"

    def test_custom_separator(self):
        opts = FlattenOptions(enabled=True, separator="|")
        results = list(flatten_entry(_entry("a|b|c"), opts))
        assert [r.message for r in results] == ["a", "b", "c"]

    def test_timestamp_and_severity_copied(self):
        opts = FlattenOptions(enabled=True)
        src = _entry("p\nq")
        results = list(flatten_entry(src, opts))
        for r in results:
            assert r.timestamp == src.timestamp
            assert r.severity == src.severity


class TestFlattenEntries:
    def test_disabled_passes_through(self):
        opts = FlattenOptions(enabled=False)
        entries = [_entry("a\nb"), _entry("c")]
        results = list(flatten_entries(entries, opts))
        assert len(results) == 2

    def test_enabled_expands_all(self):
        opts = FlattenOptions(enabled=True)
        entries = [_entry("a\nb"), _entry("c\nd")]
        results = list(flatten_entries(entries, opts))
        assert len(results) == 4
