"""Tests for logslice.alerter."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from logslice.alerter import AlertOptions, alert_entries
from logslice.parser import LogEntry


def _entry(
    severity: str = "ERROR",
    message: str = "boom",
    ts_offset: float = 0.0,
) -> LogEntry:
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    return LogEntry(
        timestamp=base + timedelta(seconds=ts_offset),
        severity=severity,
        message=message,
        raw=f"{severity} {message}",
        extra={},
    )


class TestAlertOptions:
    def test_defaults(self):
        o = AlertOptions()
        assert o.severity == "ERROR"
        assert o.threshold == 3
        assert o.window_seconds == 60.0
        assert o.alert_tag == "ALERT"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            AlertOptions(severity="VERBOSE")

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            AlertOptions(threshold=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            AlertOptions(window_seconds=-1.0)

    def test_empty_alert_tag_raises(self):
        with pytest.raises(ValueError, match="alert_tag"):
            AlertOptions(alert_tag="")

    def test_severity_normalised_to_upper(self):
        o = AlertOptions(severity="warning")
        assert o.severity == "WARNING"


def _run(entries: List[LogEntry], **kwargs) -> List[LogEntry]:
    opts = AlertOptions(**kwargs) if kwargs else AlertOptions()
    return list(alert_entries(entries, opts))


class TestAlertEntries:
    def test_no_entries_yields_nothing(self):
        assert _run([]) == []

    def test_below_threshold_no_tag(self):
        entries = [_entry(ts_offset=i) for i in range(2)]
        result = _run(entries, threshold=3)
        for e in result:
            assert "ALERT" not in e.extra

    def test_at_threshold_tags_entries(self):
        entries = [_entry(ts_offset=i) for i in range(3)]
        result = _run(entries, threshold=3, window_seconds=60.0)
        tagged = [e for e in result if e.extra.get("ALERT") == "true"]
        assert len(tagged) >= 3

    def test_low_severity_entries_pass_through_untagged(self):
        entries = [_entry(severity="INFO", ts_offset=i) for i in range(5)]
        result = _run(entries, severity="ERROR", threshold=3)
        for e in result:
            assert "ALERT" not in e.extra

    def test_entries_outside_window_not_counted(self):
        entries = [
            _entry(ts_offset=0),
            _entry(ts_offset=1),
            _entry(ts_offset=120),  # outside 60-second window
        ]
        result = _run(entries, threshold=3, window_seconds=60.0)
        tagged = [e for e in result if e.extra.get("ALERT") == "true"]
        assert len(tagged) == 0

    def test_custom_alert_tag(self):
        entries = [_entry(ts_offset=i) for i in range(3)]
        result = _run(entries, threshold=3, alert_tag="FIRE", window_seconds=60.0)
        tagged = [e for e in result if e.extra.get("FIRE") == "true"]
        assert len(tagged) >= 1

    def test_none_opts_uses_defaults(self):
        entries = [_entry(ts_offset=i) for i in range(2)]
        result = list(alert_entries(entries, None))
        assert len(result) == 2
