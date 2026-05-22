"""Integration tests: splitter wired through the pipeline via iter_split_entries."""

from __future__ import annotations

import tempfile
import os
from datetime import datetime
from typing import List

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.splitter import SplitOptions, iter_split_entries, split_entries


def _entry(severity: str = "INFO", message: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 6, 1, 10, 0, 0),
        severity=severity,
        message=message,
        raw=f"2024-06-01T10:00:00 {severity} {message}",
        tags={},
    )


def _run_pipeline(entries: List[LogEntry], min_severity: str = "DEBUG") -> List[tuple]:
    """Filter then split, returning (key, entry) pairs."""
    filtered = filter_entries(entries, FilterOptions(min_severity=min_severity))
    return list(iter_split_entries(filtered))


class TestPipelineSplitter:
    def test_only_matching_severity_split(self):
        entries = [_entry("DEBUG"), _entry("WARNING"), _entry("ERROR")]
        pairs = _run_pipeline(entries, min_severity="WARNING")
        keys = [k for k, _ in pairs]
        assert "DEBUG" not in keys
        assert "WARNING" in keys
        assert "ERROR" in keys

    def test_split_counts_match_filter_output(self):
        entries = [_entry("INFO")] * 3 + [_entry("ERROR")] * 2
        pairs = _run_pipeline(entries, min_severity="INFO")
        from collections import Counter
        counts = Counter(k for k, _ in pairs)
        assert counts["INFO"] == 3
        assert counts["ERROR"] == 2

    def test_split_writes_only_filtered_entries_to_disk(self):
        entries = [_entry("DEBUG", "low"), _entry("ERROR", "high")]
        with tempfile.TemporaryDirectory() as tmpdir:
            filtered = list(filter_entries(entries, FilterOptions(min_severity="ERROR")))
            counts = split_entries(filtered, SplitOptions(output_dir=tmpdir))
            assert "DEBUG" not in counts
            assert counts.get("ERROR") == 1
            assert not os.path.exists(os.path.join(tmpdir, "DEBUG.log"))
            assert os.path.exists(os.path.join(tmpdir, "ERROR.log"))

    def test_no_entries_after_filter_produces_no_files(self):
        entries = [_entry("DEBUG")]
        with tempfile.TemporaryDirectory() as tmpdir:
            filtered = list(filter_entries(entries, FilterOptions(min_severity="ERROR")))
            counts = split_entries(filtered, SplitOptions(output_dir=tmpdir))
            assert counts == {}
            assert os.listdir(tmpdir) == []
