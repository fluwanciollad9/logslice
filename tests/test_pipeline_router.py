"""Integration tests: router wired into the pipeline via PipelineOptions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from logslice.parser import LogEntry
from logslice.router import RouteRule, RouterOptions, route_to_dict
from logslice.filter import FilterOptions, filter_entries


def _entry(severity: str = "INFO", message: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=f"{severity} {message}",
    )


def _run(
    entries: List[LogEntry],
    min_severity: str = "DEBUG",
    rules: list | None = None,
) -> dict:
    """Filter entries then route them."""
    filter_opts = FilterOptions(min_severity=min_severity)
    filtered = list(filter_entries(entries, filter_opts))
    router_opts = RouterOptions(rules=rules or [])
    return route_to_dict(filtered, router_opts)


class TestPipelineRouter:
    def test_only_filtered_entries_are_routed(self):
        entries = [
            _entry("DEBUG", "trace"),
            _entry("ERROR", "boom"),
        ]
        result = _run(entries, min_severity="ERROR")
        all_entries = [e for ch_entries in result.values() for e in ch_entries]
        assert len(all_entries) == 1
        assert all_entries[0].severity == "ERROR"

    def test_routing_after_filter_respects_rules(self):
        entries = [
            _entry("ERROR", "db error"),
            _entry("ERROR", "network error"),
            _entry("INFO", "all good"),
        ]
        rules = [
            RouteRule(channel="db", keyword="db"),
            RouteRule(channel="net", keyword="network"),
        ]
        result = _run(entries, min_severity="INFO", rules=rules)
        assert len(result.get("db", [])) == 1
        assert len(result.get("net", [])) == 1
        assert len(result.get("default", [])) == 1

    def test_total_count_preserved_after_filter_and_route(self):
        entries = [_entry("INFO"), _entry("WARNING"), _entry("ERROR")]
        result = _run(entries, min_severity="INFO")
        total = sum(len(v) for v in result.values())
        assert total == 3
