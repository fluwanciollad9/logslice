"""Integration tests: tagger wired into the pipeline."""

from __future__ import annotations

from datetime import datetime

from logslice.parser import LogEntry
from logslice.tagger import TagRule, TaggerOptions, tag_entries
from logslice.filter import FilterOptions, filter_entries


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 6, 1, 8, 0, 0),
        severity=severity,
        message=message,
        raw=f"2024-06-01 08:00:00 {severity} {message}",
    )


class TestPipelineTagger:
    """Verify that tagging composes correctly with other pipeline stages."""

    def _run(self, entries, rules, include_keyword=None):
        opts = TaggerOptions(rules=rules)
        tagged = tag_entries(entries, opts)
        if include_keyword:
            fopts = FilterOptions(include_keywords=[include_keyword])
            tagged = filter_entries(tagged, fopts)
        return list(tagged)

    def test_tagged_entries_pass_through_filter(self):
        entries = [
            _entry("disk usage critical", severity="ERROR"),
            _entry("all good"),
        ]
        rules = [TagRule(tag="disk", keyword="disk")]
        result = self._run(entries, rules, include_keyword="disk")
        assert len(result) == 1
        assert "disk" in result[0].tags

    def test_tags_preserved_after_filter(self):
        entries = [_entry("timeout error", severity="ERROR")]
        rules = [
            TagRule(tag="timeout", keyword="timeout"),
            TagRule(tag="error", severity="ERROR"),
        ]
        result = self._run(entries, rules)
        assert "timeout" in result[0].tags
        assert "error" in result[0].tags

    def test_untagged_entry_has_empty_tags_after_pipeline(self):
        entries = [_entry("routine heartbeat")]
        result = self._run(entries, [])
        assert result[0].tags == []

    def test_multiple_entries_tagged_independently(self):
        entries = [
            _entry("slow query"),
            _entry("timeout reached"),
            _entry("normal operation"),
        ]
        rules = [
            TagRule(tag="slow", keyword="slow"),
            TagRule(tag="timeout", keyword="timeout"),
        ]
        result = self._run(entries, rules)
        assert result[0].tags == ["slow"]
        assert result[1].tags == ["timeout"]
        assert result[2].tags == []
