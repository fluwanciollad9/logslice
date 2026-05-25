"""Integration tests: alerter wired through the pipeline."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from logslice.alerter import AlertOptions, alert_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(
    severity: str = "ERROR",
    message: str = "fail",
    ts_offset: float = 0.0,
) -> LogEntry:
    base = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    return LogEntry(
        timestamp=base + timedelta(seconds=ts_offset),
        severity=severity,
        message=message,
        raw=f"{severity} {message}",
        extra={},
    )


def _run(
    entries: List[LogEntry],
    filter_severity: str = "DEBUG",
    alert_severity: str = "ERROR",
    threshold: int = 3,
    window: float = 60.0,
) -> List[LogEntry]:
    fopts = FilterOptions(min_severity=filter_severity)
    filtered = list(filter_entries(entries, fopts))
    aopts = AlertOptions(severity=alert_severity, threshold=threshold, window_seconds=window)
    return list(alert_entries(filtered, aopts))


class TestPipelineAlerter:
    def test_alert_disabled_when_threshold_high(self):
        entries = [_entry(ts_offset=i) for i in range(2)]
        result = _run(entries, threshold=10)
        tagged = [e for e in result if "ALERT" in e.extra]
        assert tagged == []

    def test_alert_fires_after_filter(self):
        entries = [
            _entry(severity="DEBUG", ts_offset=0),  # filtered out
            _entry(severity="ERROR", ts_offset=1),
            _entry(severity="ERROR", ts_offset=2),
            _entry(severity="ERROR", ts_offset=3),
        ]
        result = _run(entries, filter_severity="ERROR", threshold=3, window=60.0)
        tagged = [e for e in result if e.extra.get("ALERT") == "true"]
        assert len(tagged) >= 3

    def test_only_filtered_entries_reach_alerter(self):
        entries = [
            _entry(severity="INFO", ts_offset=i) for i in range(5)
        ] + [
            _entry(severity="ERROR", ts_offset=i) for i in range(5)
        ]
        result = _run(entries, filter_severity="ERROR", threshold=3)
        severities = {e.severity for e in result}
        assert severities == {"ERROR"}
