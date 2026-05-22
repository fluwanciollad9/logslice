"""Tests for logslice.splitter."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from typing import Optional

import pytest

from logslice.parser import LogEntry
from logslice.splitter import SplitOptions, _entry_key, iter_split_entries, split_entries


def _entry(
    severity: str = "INFO",
    message: str = "hello",
    tags: Optional[dict] = None,
    raw: str = "",
) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
        raw=raw or f"2024-01-01T12:00:00 {severity} {message}",
        tags=tags or {},
    )


class TestSplitOptions:
    def test_defaults(self):
        opts = SplitOptions()
        assert opts.by == "severity"
        assert opts.output_dir == "."

    def test_invalid_by_raises(self):
        with pytest.raises(ValueError, match="by must be"):
            SplitOptions(by="unknown")

    def test_tag_without_key_raises(self):
        with pytest.raises(ValueError, match="tag_key is required"):
            SplitOptions(by="tag")

    def test_tag_with_key_valid(self):
        opts = SplitOptions(by="tag", tag_key="env")
        assert opts.tag_key == "env"


class TestEntryKey:
    def test_severity_key_uppercased(self):
        entry = _entry(severity="warning")
        opts = SplitOptions(by="severity")
        assert _entry_key(entry, opts) == "WARNING"

    def test_missing_severity_returns_unknown(self):
        entry = _entry(severity=None)  # type: ignore[arg-type]
        opts = SplitOptions(by="severity")
        assert _entry_key(entry, opts) == "UNKNOWN"

    def test_tag_key_present(self):
        entry = _entry(tags={"env": "prod"})
        opts = SplitOptions(by="tag", tag_key="env")
        assert _entry_key(entry, opts) == "prod"

    def test_tag_key_absent_returns_untagged(self):
        entry = _entry(tags={})
        opts = SplitOptions(by="tag", tag_key="env")
        assert _entry_key(entry, opts) == "UNTAGGED"


class TestIterSplitEntries:
    def test_groups_by_severity(self):
        entries = [_entry("INFO"), _entry("ERROR"), _entry("INFO")]
        pairs = list(iter_split_entries(entries))
        keys = [k for k, _ in pairs]
        assert keys == ["INFO", "ERROR", "INFO"]

    def test_groups_by_tag(self):
        entries = [
            _entry(tags={"env": "prod"}),
            _entry(tags={"env": "dev"}),
        ]
        opts = SplitOptions(by="tag", tag_key="env")
        keys = [k for k, _ in iter_split_entries(entries, opts)]
        assert keys == ["prod", "dev"]


class TestSplitEntries:
    def test_writes_files_per_severity(self):
        entries = [_entry("INFO"), _entry("ERROR"), _entry("INFO")]
        with tempfile.TemporaryDirectory() as tmpdir:
            counts = split_entries(entries, SplitOptions(output_dir=tmpdir))
            assert counts["INFO"] == 2
            assert counts["ERROR"] == 1
            assert os.path.exists(os.path.join(tmpdir, "INFO.log"))
            assert os.path.exists(os.path.join(tmpdir, "ERROR.log"))

    def test_filename_template_respected(self):
        entries = [_entry("DEBUG")]
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = SplitOptions(output_dir=tmpdir, filename_template="slice_{key}.txt")
            split_entries(entries, opts)
            assert os.path.exists(os.path.join(tmpdir, "slice_DEBUG.txt"))

    def test_empty_entries_returns_empty_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            counts = split_entries([], SplitOptions(output_dir=tmpdir))
            assert counts == {}
