"""Tests for logslice.stats.SliceStats."""
import pytest

from logslice.stats import SliceStats


def _populated() -> SliceStats:
    s = SliceStats()
    s.record_match("info")
    s.record_match("info")
    s.record_match("error")
    s.record_unparseable()
    s.record_severity_skip("debug")
    s.record_time_skip(before=True)
    s.record_time_skip(before=False)
    return s


class TestSliceStats:
    def test_total_lines_counts_all_records(self):
        s = _populated()
        assert s.total_lines == 7

    def test_matched_lines(self):
        s = _populated()
        assert s.matched_lines == 3

    def test_skipped_lines_is_complement(self):
        s = _populated()
        assert s.skipped_lines == 4

    def test_skipped_unparseable(self):
        s = _populated()
        assert s.skipped_unparseable == 1

    def test_skipped_severity(self):
        s = _populated()
        assert s.skipped_severity == 1

    def test_skipped_before_start(self):
        s = _populated()
        assert s.skipped_before_start == 1

    def test_skipped_after_end(self):
        s = _populated()
        assert s.skipped_after_end == 1

    def test_severity_counts_include_matched_and_skipped(self):
        s = _populated()
        assert s.severity_counts["info"] == 2
        assert s.severity_counts["error"] == 1
        assert s.severity_counts["debug"] == 1

    def test_match_rate_calculation(self):
        s = _populated()
        # parseable = 7 - 1 = 6; matched = 3
        assert s.match_rate == pytest.approx(0.5)

    def test_match_rate_none_when_all_unparseable(self):
        s = SliceStats()
        s.record_unparseable()
        assert s.match_rate is None

    def test_match_rate_none_for_empty_stats(self):
        s = SliceStats()
        assert s.match_rate is None

    def test_summary_contains_key_labels(self):
        s = _populated()
        summary = s.summary()
        assert "Total lines" in summary
        assert "Matched" in summary
        assert "Severity breakdown" in summary

    def test_summary_shows_severity_counts(self):
        s = _populated()
        assert "info" in s.summary()
        assert "error" in s.summary()

    def test_empty_stats_summary_has_no_severity_breakdown(self):
        s = SliceStats()
        assert "Severity breakdown" not in s.summary()
