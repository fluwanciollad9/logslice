"""Tests for logslice.filter."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.filter import FilterOptions, filter_entries, _matches
from logslice.parser import LogEntry


def _entry(message: str) -> LogEntry:
    return LogEntry(
        raw=message,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity="INFO",
        message=message,
    )


class TestMatches:
    def test_no_filters_always_matches(self):
        assert _matches("anything", FilterOptions()) is True

    def test_include_keyword_present(self):
        opts = FilterOptions(include_keywords=["error"])
        assert _matches("disk error occurred", opts) is True

    def test_include_keyword_absent(self):
        opts = FilterOptions(include_keywords=["error"])
        assert _matches("all systems nominal", opts) is False

    def test_exclude_keyword_present(self):
        opts = FilterOptions(exclude_keywords=["debug"])
        assert _matches("debug info here", opts) is False

    def test_exclude_keyword_absent(self):
        opts = FilterOptions(exclude_keywords=["debug"])
        assert _matches("error in module", opts) is True

    def test_include_pattern_matches(self):
        opts = FilterOptions(include_pattern=r"user\s+\d+")
        assert _matches("created user 42", opts) is True

    def test_include_pattern_no_match(self):
        opts = FilterOptions(include_pattern=r"user\s+\d+")
        assert _matches("no relevant data", opts) is False

    def test_exclude_pattern_matches(self):
        opts = FilterOptions(exclude_pattern=r"healthcheck")
        assert _matches("GET /healthcheck 200", opts) is False

    def test_case_sensitive_keyword(self):
        opts = FilterOptions(include_keywords=["ERROR"], case_sensitive=True)
        assert _matches("error occurred", opts) is False
        assert _matches("ERROR occurred", opts) is True

    def test_multiple_include_keywords_all_required(self):
        opts = FilterOptions(include_keywords=["login", "failed"])
        assert _matches("login attempt failed", opts) is True
        assert _matches("login attempt", opts) is False

    def test_include_and_exclude_keyword_conflict(self):
        """Exclude takes precedence when both include and exclude keywords match."""
        opts = FilterOptions(include_keywords=["error"], exclude_keywords=["error"])
        assert _matches("error occurred", opts) is False


class TestFilterEntries:
    def test_yields_matching_entries(self):
        entries = [_entry("disk error"), _entry("all ok"), _entry("another error")]
        opts = FilterOptions(include_keywords=["error"])
        result = list(filter_entries(entries, opts))
        assert len(result) == 2
        assert all("error" in e.message for e in result)

    def test_empty_input_yields_nothing(self):
        opts = FilterOptions(include_keywords=["x"])
        assert list(filter_entries([], opts)) == []

    def test_no_filters_yields_all(self):
        entries = [_entry("a"), _entry("b"), _entry("c")]
        result = list(filter_entries(entries, FilterOptions()))
        assert len(result) == 3

    def test_exclude_removes_entries(self):
        entries = [_entry("GET /healthcheck"), _entry("POST /api/data")]
        opts = FilterOptions(exclude_keywords=["healthcheck"])
        result = list(filter_entries(entries, opts))
        assert len(result) == 1
        assert result[0].message == "POST /api/data"
