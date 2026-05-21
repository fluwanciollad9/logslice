"""Tests for the parser and slicer modules."""

from datetime import datetime

import pytest

from logslice.parser import parse_line
from logslice.slicer import slice_lines

SAMPLE_LINES = [
    "2024-03-01 08:00:00 [DEBUG] Starting up",
    "2024-03-01 09:15:00 [INFO] Server ready",
    "2024-03-01 10:30:00 [WARNING] High memory usage",
    "2024-03-01 11:45:00 [ERROR] Connection refused",
    "2024-03-01 12:00:00 [CRITICAL] Disk full",
    "not a log line at all",
    "2024-03-01 13:00:00 [WARN] Deprecated API call",
]


class TestParseLine:
    def test_parses_standard_line(self):
        entry = parse_line("2024-03-01 09:15:00 [INFO] Server ready")
        assert entry is not None
        assert entry.level == "INFO"
        assert entry.message == "Server ready"
        assert entry.timestamp == datetime(2024, 3, 1, 9, 15, 0)

    def test_warn_normalised_to_warning(self):
        entry = parse_line("2024-03-01 13:00:00 [WARN] Deprecated API call")
        assert entry is not None
        assert entry.level == "WARNING"

    def test_unparseable_line_returns_none(self):
        assert parse_line("not a log line at all") is None

    def test_iso_timestamp_with_t(self):
        entry = parse_line("2024-03-01T09:15:00 [ERROR] boom")
        assert entry is not None
        assert entry.timestamp == datetime(2024, 3, 1, 9, 15, 0)


class TestSliceLines:
    def test_no_filters_returns_all_parseable(self):
        results = list(slice_lines(SAMPLE_LINES))
        assert len(results) == 6  # excludes the unparseable line

    def test_start_filter(self):
        start = datetime(2024, 3, 1, 10, 0, 0)
        results = list(slice_lines(SAMPLE_LINES, start=start))
        assert all(e.timestamp >= start for e in results)
        assert len(results) == 4

    def test_end_filter(self):
        end = datetime(2024, 3, 1, 10, 0, 0)
        results = list(slice_lines(SAMPLE_LINES, end=end))
        assert all(e.timestamp <= end for e in results)
        assert len(results) == 2

    def test_time_range_filter(self):
        start = datetime(2024, 3, 1, 9, 0, 0)
        end = datetime(2024, 3, 1, 11, 0, 0)
        results = list(slice_lines(SAMPLE_LINES, start=start, end=end))
        assert len(results) == 2
        assert {e.level for e in results} == {"INFO", "WARNING"}

    def test_min_level_error(self):
        results = list(slice_lines(SAMPLE_LINES, min_level="ERROR"))
        assert all(e.level in {"ERROR", "CRITICAL"} for e in results)
        assert len(results) == 2

    def test_min_level_debug_includes_all(self):
        results = list(slice_lines(SAMPLE_LINES, min_level="DEBUG"))
        assert len(results) == 6

    def test_combined_filters(self):
        start = datetime(2024, 3, 1, 10, 0, 0)
        results = list(slice_lines(SAMPLE_LINES, start=start, min_level="ERROR"))
        assert len(results) == 2
        assert all(e.level in {"ERROR", "CRITICAL"} for e in results)
