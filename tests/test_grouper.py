"""Tests for logslice.grouper."""
from __future__ import annotations

import pytest

from logslice.grouper import GroupOptions, group_entries, iter_group_entries
from logslice.parser import LogEntry
from datetime import datetime


def _entry(severity: str = "INFO", message: str = "msg", tags=None) -> LogEntry:
    e = LogEntry(
        raw=f"{severity} {message}",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
    )
    if tags is not None:
        object.__setattr__(e, "tags", tags)
    return e


class TestGroupOptions:
    def test_defaults(self):
        opts = GroupOptions()
        assert opts.by == "severity"
        assert opts.sort_keys is True

    def test_invalid_by_raises(self):
        with pytest.raises(ValueError, match="Invalid group-by"):
            GroupOptions(by="banana")

    def test_valid_by_values(self):
        for val in ("severity", "tag", "source"):
            opts = GroupOptions(by=val)
            assert opts.by == val


class TestGroupEntries:
    def test_empty_input_returns_empty(self):
        result = group_entries([])
        assert result == {}

    def test_groups_by_severity(self):
        entries = [_entry("INFO"), _entry("ERROR"), _entry("INFO")]
        result = group_entries(entries)
        assert set(result.keys()) == {"INFO", "ERROR"}
        assert len(result["INFO"]) == 2
        assert len(result["ERROR"]) == 1

    def test_unknown_severity_uses_unknown_key(self):
        e = LogEntry(raw="msg", timestamp=None, severity=None, message="msg")
        result = group_entries([e])
        assert "UNKNOWN" in result

    def test_group_by_tag_untagged(self):
        entries = [_entry("INFO")]
        result = group_entries(entries, GroupOptions(by="tag"))
        assert "(untagged)" in result

    def test_group_by_tag_with_tags(self):
        entries = [_entry("INFO", tags=["auth"]), _entry("WARN", tags=["auth"])]
        result = group_entries(entries, GroupOptions(by="tag"))
        assert "auth" in result
        assert len(result["auth"]) == 2

    def test_group_by_source_unknown(self):
        entries = [_entry("INFO")]
        result = group_entries(entries, GroupOptions(by="source"))
        assert "(unknown)" in result


class TestIterGroupEntries:
    def test_yields_key_and_list(self):
        entries = [_entry("DEBUG"), _entry("ERROR")]
        pairs = list(iter_group_entries(entries))
        assert all(isinstance(k, str) and isinstance(v, list) for k, v in pairs)

    def test_keys_sorted_by_default(self):
        entries = [_entry("WARNING"), _entry("DEBUG"), _entry("ERROR")]
        keys = [k for k, _ in iter_group_entries(entries)]
        assert keys == sorted(keys)

    def test_keys_unsorted_when_disabled(self):
        entries = [_entry("WARNING"), _entry("DEBUG"), _entry("ERROR")]
        opts = GroupOptions(sort_keys=False)
        keys = [k for k, _ in iter_group_entries(entries, opts)]
        # order is insertion order — just verify all keys present
        assert set(keys) == {"WARNING", "DEBUG", "ERROR"}

    def test_total_entries_preserved(self):
        entries = [_entry("INFO")] * 5 + [_entry("ERROR")] * 3
        total = sum(len(v) for _, v in iter_group_entries(entries))
        assert total == 8
