"""Tests for logslice.classifier."""
from __future__ import annotations

import pytest
from datetime import datetime

from logslice.parser import LogEntry
from logslice.classifier import (
    ClassifyRule,
    ClassifyOptions,
    classify_entries,
)


def _entry(message: str, severity: str = "INFO", tags: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
        raw=f"2024-01-01T12:00:00 {severity} {message}",
        tags=tags or {},
    )


# --- ClassifyRule validation ---

class TestClassifyRule:
    def test_empty_category_raises(self):
        with pytest.raises(ValueError, match="category"):
            ClassifyRule(category="", keyword="foo")

    def test_no_condition_raises(self):
        with pytest.raises(ValueError, match="at least one condition"):
            ClassifyRule(category="x")

    def test_keyword_only_valid(self):
        rule = ClassifyRule(category="db", keyword="database")
        assert rule.category == "db"

    def test_invalid_regex_raises(self):
        with pytest.raises(ValueError, match="invalid pattern"):
            ClassifyRule(category="x", pattern="[unclosed")

    def test_invalid_min_severity_raises(self):
        with pytest.raises(ValueError, match="unknown severity"):
            ClassifyRule(category="x", min_severity="VERBOSE")


# --- ClassifyOptions validation ---

class TestClassifyOptions:
    def test_defaults(self):
        opts = ClassifyOptions()
        assert opts.default_category == "uncategorized"
        assert opts.tag_key == "category"
        assert opts.rules == []

    def test_empty_tag_key_raises(self):
        with pytest.raises(ValueError, match="tag_key"):
            ClassifyOptions(tag_key="")


# --- classify_entries ---

class TestClassifyEntries:
    def test_no_rules_passes_through(self):
        entries = [_entry("hello"), _entry("world")]
        result = list(classify_entries(entries))
        assert result == entries

    def test_none_opts_passes_through(self):
        entries = [_entry("hello")]
        result = list(classify_entries(entries, opts=None))
        assert result == entries

    def test_keyword_match_assigns_category(self):
        opts = ClassifyOptions(rules=[ClassifyRule(category="db", keyword="database")])
        result = list(classify_entries([_entry("database timeout")], opts))
        assert result[0].tags["category"] == "db"

    def test_no_match_uses_default_category(self):
        opts = ClassifyOptions(rules=[ClassifyRule(category="db", keyword="database")])
        result = list(classify_entries([_entry("network error")], opts))
        assert result[0].tags["category"] == "uncategorized"

    def test_pattern_match(self):
        opts = ClassifyOptions(rules=[ClassifyRule(category="timeout", pattern=r"timed?\s*out")])
        result = list(classify_entries([_entry("connection timed out")], opts))
        assert result[0].tags["category"] == "timeout"

    def test_min_severity_match(self):
        opts = ClassifyOptions(rules=[ClassifyRule(category="alert", min_severity="ERROR")])
        result = list(classify_entries([_entry("disk full", severity="ERROR")], opts))
        assert result[0].tags["category"] == "alert"

    def test_min_severity_no_match_below_threshold(self):
        opts = ClassifyOptions(rules=[ClassifyRule(category="alert", min_severity="ERROR")])
        result = list(classify_entries([_entry("debug info", severity="DEBUG")], opts))
        assert result[0].tags["category"] == "uncategorized"

    def test_first_matching_rule_wins(self):
        opts = ClassifyOptions(rules=[
            ClassifyRule(category="first", keyword="foo"),
            ClassifyRule(category="second", keyword="foo"),
        ])
        result = list(classify_entries([_entry("foo bar")], opts))
        assert result[0].tags["category"] == "first"

    def test_custom_tag_key(self):
        opts = ClassifyOptions(
            rules=[ClassifyRule(category="auth", keyword="login")],
            tag_key="kind",
        )
        result = list(classify_entries([_entry("user login")], opts))
        assert "kind" in result[0].tags
        assert result[0].tags["kind"] == "auth"

    def test_existing_tags_preserved(self):
        entry = _entry("login failed", tags={"source": "app"})
        opts = ClassifyOptions(rules=[ClassifyRule(category="auth", keyword="login")])
        result = list(classify_entries([entry], opts))
        assert result[0].tags["source"] == "app"
        assert result[0].tags["category"] == "auth"
