"""Tests for logslice.router."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.router import RouteRule, RouterOptions, route_entries, route_to_dict


def _entry(severity: str = "INFO", message: str = "hello world") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=f"{severity} {message}",
    )


# ---------------------------------------------------------------------------
# RouteRule
# ---------------------------------------------------------------------------

class TestRouteRule:
    def test_empty_channel_raises(self):
        with pytest.raises(ValueError, match="channel"):
            RouteRule(channel="", severity="ERROR")

    def test_no_condition_raises(self):
        with pytest.raises(ValueError, match="severity or keyword"):
            RouteRule(channel="ch")

    def test_severity_only_valid(self):
        rule = RouteRule(channel="errors", severity="ERROR")
        assert rule.matches(_entry("ERROR"))
        assert not rule.matches(_entry("INFO"))

    def test_keyword_only_valid(self):
        rule = RouteRule(channel="db", keyword="database")
        assert rule.matches(_entry(message="database timeout"))
        assert not rule.matches(_entry(message="network error"))

    def test_severity_and_keyword_both_must_match(self):
        rule = RouteRule(channel="ch", severity="ERROR", keyword="crash")
        assert rule.matches(_entry("ERROR", "system crash"))
        assert not rule.matches(_entry("INFO", "system crash"))
        assert not rule.matches(_entry("ERROR", "all good"))

    def test_severity_match_is_case_insensitive(self):
        rule = RouteRule(channel="ch", severity="error")
        assert rule.matches(_entry("ERROR"))

    def test_keyword_match_is_case_insensitive(self):
        rule = RouteRule(channel="ch", keyword="CRASH")
        assert rule.matches(_entry(message="system crash"))


# ---------------------------------------------------------------------------
# RouterOptions
# ---------------------------------------------------------------------------

class TestRouterOptions:
    def test_defaults(self):
        opts = RouterOptions()
        assert opts.default_channel == "default"
        assert opts.emit_unmatched is True
        assert opts.rules == []

    def test_empty_default_channel_raises(self):
        with pytest.raises(ValueError, match="default_channel"):
            RouterOptions(default_channel="")


# ---------------------------------------------------------------------------
# route_entries / route_to_dict
# ---------------------------------------------------------------------------

class TestRouteEntries:
    def test_no_rules_all_go_to_default(self):
        entries = [_entry("INFO"), _entry("ERROR")]
        result = list(route_entries(entries))
        assert all(ch == "default" for ch, _ in result)
        assert len(result) == 2

    def test_first_matching_rule_wins(self):
        rules = [
            RouteRule(channel="errors", severity="ERROR"),
            RouteRule(channel="also_errors", severity="ERROR"),
        ]
        opts = RouterOptions(rules=rules)
        result = list(route_entries([_entry("ERROR")], opts))
        assert result[0][0] == "errors"

    def test_unmatched_goes_to_default_channel(self):
        opts = RouterOptions(
            rules=[RouteRule(channel="errors", severity="ERROR")],
            default_channel="misc",
        )
        result = list(route_entries([_entry("INFO")], opts))
        assert result[0][0] == "misc"

    def test_emit_unmatched_false_drops_unmatched(self):
        opts = RouterOptions(
            rules=[RouteRule(channel="errors", severity="ERROR")],
            emit_unmatched=False,
        )
        result = list(route_entries([_entry("INFO"), _entry("ERROR")], opts))
        assert len(result) == 1
        assert result[0][0] == "errors"

    def test_route_to_dict_groups_by_channel(self):
        opts = RouterOptions(
            rules=[RouteRule(channel="errors", severity="ERROR")]
        )
        entries = [_entry("ERROR"), _entry("INFO"), _entry("ERROR")]
        d = route_to_dict(entries, opts)
        assert len(d["errors"]) == 2
        assert len(d["default"]) == 1

    def test_none_options_uses_defaults(self):
        entries = [_entry()]
        result = list(route_entries(entries, None))
        assert result[0][0] == "default"
