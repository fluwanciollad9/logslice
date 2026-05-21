"""Integration tests: slice_lines / slice_file with stats collection."""
from __future__ import annotations

import io
import tempfile
import os
from datetime import datetime, timezone

import pytest

from logslice.slicer import slice_lines, slice_file

_LINES = [
    "2024-01-15T10:00:00Z INFO  service started",
    "2024-01-15T10:01:00Z DEBUG checking config",
    "2024-01-15T10:02:00Z WARNING disk usage high",
    "2024-01-15T10:03:00Z ERROR disk full",
    "not a log line at all",
    "2024-01-15T10:04:00Z INFO  recovered",
]


class TestSliceLinesStats:
    def _run(self, **kwargs):
        gen, stats = slice_lines(_LINES, collect_stats=True, **kwargs)
        entries = list(gen)
        return entries, stats

    def test_stats_returned_when_requested(self):
        _, stats = self._run()
        assert stats is not None

    def test_stats_none_when_not_requested(self):
        gen, stats = slice_lines(_LINES)
        list(gen)  # exhaust
        assert stats is None

    def test_total_lines_matches_input(self):
        _, stats = self._run()
        assert stats.total_lines == len(_LINES)

    def test_unparseable_counted(self):
        _, stats = self._run()
        assert stats.skipped_unparseable == 1

    def test_matched_without_filters(self):
        entries, stats = self._run()
        assert stats.matched_lines == 5
        assert len(entries) == 5

    def test_severity_filter_updates_skipped_severity(self):
        _, stats = self._run(min_severity="warning")
        assert stats.skipped_severity == 2  # INFO + DEBUG

    def test_time_filter_before_start(self):
        start = datetime(2024, 1, 15, 10, 2, 0, tzinfo=timezone.utc)
        _, stats = self._run(start=start)
        assert stats.skipped_before_start == 2  # 10:00 and 10:01

    def test_time_filter_after_end(self):
        end = datetime(2024, 1, 15, 10, 2, 0, tzinfo=timezone.utc)
        _, stats = self._run(end=end)
        assert stats.skipped_after_end == 2  # 10:03 and 10:04

    def test_severity_counts_populated(self):
        _, stats = self._run()
        assert stats.severity_counts.get("info", 0) == 2
        assert stats.severity_counts.get("debug", 0) == 1
        assert stats.severity_counts.get("warning", 0) == 1
        assert stats.severity_counts.get("error", 0) == 1


class TestSliceFileStats:
    def _make_tmp(self, lines):
        fd, path = tempfile.mkstemp(suffix=".log")
        with os.fdopen(fd, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        return path

    def test_stats_collected_from_file(self):
        path = self._make_tmp(_LINES)
        try:
            gen, stats = slice_file(path, collect_stats=True)
            entries = list(gen)
            assert stats is not None
            assert stats.total_lines == len(_LINES)
            assert stats.matched_lines == len(entries)
        finally:
            os.unlink(path)
