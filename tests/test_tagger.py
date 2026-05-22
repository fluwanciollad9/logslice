"""Tests for logslice.tagger."""

from __future__ import annotations

import pytest
from datetime import datetime

from logslice.parser import LogEntry
from logslice.tagger import TagRule, TaggerOptions, tag_entries


def _entry(message: str = "hello world", severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
        raw=f"2024-01-01 12:00:00 {severity} {message}",
    )


class TestTagRule:
    def test_empty_tag_raises(self):
        with pytest.raises(ValueError, match="tag must be"):
            TagRule(tag="", keyword="error")

    def test_no_condition_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            TagRule(tag="mytag")

    def test_keyword_only_valid(self):
        rule = TagRule(tag="k", keyword="timeout")
        assert rule.keyword == "timeout"

    def test_severity_only_valid(self):
        rule = TagRule(tag="s", severity="ERROR")
        assert rule.severity == "ERROR"


class TestTagEntries:
    def test_no_rules_produces_empty_tags(self):
        entries = [_entry()]
        result = list(tag_entries(entries))
        assert result[0].tags == []

    def test_keyword_match_applies_tag(self):
        rule = TagRule(tag="timeout", keyword="timeout")
        opts = TaggerOptions(rules=[rule])
        entry = _entry(message="connection timeout occurred")
        result = list(tag_entries([entry], opts))
        assert "timeout" in result[0].tags

    def test_keyword_no_match_no_tag(self):
        rule = TagRule(tag="timeout", keyword="timeout")
        opts = TaggerOptions(rules=[rule])
        entry = _entry(message="all systems nominal")
        result = list(tag_entries([entry], opts))
        assert result[0].tags == []

    def test_severity_match_applies_tag(self):
        rule = TagRule(tag="critical", severity="CRITICAL")
        opts = TaggerOptions(rules=[rule])
        entry = _entry(severity="CRITICAL")
        result = list(tag_entries([entry], opts))
        assert "critical" in result[0].tags

    def test_severity_case_insensitive(self):
        rule = TagRule(tag="err", severity="error")
        opts = TaggerOptions(rules=[rule])
        entry = _entry(severity="ERROR")
        result = list(tag_entries([entry], opts))
        assert "err" in result[0].tags

    def test_multi_tag_applies_all_matching(self):
        rules = [
            TagRule(tag="slow", keyword="slow"),
            TagRule(tag="db", keyword="database"),
        ]
        opts = TaggerOptions(rules=rules, multi_tag=True)
        entry = _entry(message="slow database query detected")
        result = list(tag_entries([entry], opts))
        assert "slow" in result[0].tags
        assert "db" in result[0].tags

    def test_multi_tag_false_stops_at_first_match(self):
        rules = [
            TagRule(tag="slow", keyword="slow"),
            TagRule(tag="db", keyword="database"),
        ]
        opts = TaggerOptions(rules=rules, multi_tag=False)
        entry = _entry(message="slow database query detected")
        result = list(tag_entries([entry], opts))
        assert result[0].tags == ["slow"]

    def test_original_entry_not_mutated(self):
        rule = TagRule(tag="x", keyword="hello")
        opts = TaggerOptions(rules=[rule])
        entry = _entry(message="hello")
        list(tag_entries([entry], opts))
        assert entry.tags == []

    def test_yields_all_entries(self):
        entries = [_entry(), _entry(), _entry()]
        result = list(tag_entries(entries))
        assert len(result) == 3
