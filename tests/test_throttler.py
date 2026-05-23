"""Tests for logslice.throttler."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.parser import LogEntry
from logslice.throttler import ThrottleOptions, throttle_entries


def _entry(
    msg: str = "hello",
    severity: str = "INFO",
    ts: datetime | None = None,
) -> LogEntry:
    return LogEntry(
        timestamp=ts or datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        severity=severity,
        message=msg,
        raw=f"2024-01-01T00:00:00Z {severity} {msg}",
    )


def _ts(second: int) -> datetime:
    return datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc)


class TestThrottleOptions:
    def test_defaults(self) -> None:
        opts = ThrottleOptions()
        assert opts.max_per_window == 0
        assert opts.window_seconds == 1.0
        assert opts.by_severity is False

    def test_negative_max_raises(self) -> None:
        with pytest.raises(ValueError, match="max_per_window"):
            ThrottleOptions(max_per_window=-1)

    def test_zero_window_raises(self) -> None:
        with pytest.raises(ValueError, match="window_seconds"):
            ThrottleOptions(max_per_window=1, window_seconds=0)

    def test_negative_window_raises(self) -> None:
        with pytest.raises(ValueError, match="window_seconds"):
            ThrottleOptions(max_per_window=1, window_seconds=-5.0)


class TestThrottleEntries:
    def test_disabled_passes_all(self) -> None:
        entries = [_entry(ts=_ts(i)) for i in range(10)]
        result = list(throttle_entries(entries, ThrottleOptions(max_per_window=0)))
        assert len(result) == 10

    def test_limits_within_window(self) -> None:
        # 5 entries all at the same second; limit 2 per 1-second window
        entries = [_entry(ts=_ts(0)) for _ in range(5)]
        opts = ThrottleOptions(max_per_window=2, window_seconds=1.0)
        result = list(throttle_entries(entries, opts))
        assert len(result) == 2

    def test_entries_across_windows_all_pass(self) -> None:
        # one entry per second, limit 1 per second — all should pass
        entries = [_entry(ts=_ts(i)) for i in range(5)]
        opts = ThrottleOptions(max_per_window=1, window_seconds=1.0)
        result = list(throttle_entries(entries, opts))
        assert len(result) == 5

    def test_no_timestamp_always_emitted(self) -> None:
        entries = [LogEntry(timestamp=None, severity="INFO", message="x", raw="x")]
        opts = ThrottleOptions(max_per_window=0)
        result = list(throttle_entries(entries, opts))
        assert len(result) == 1

    def test_by_severity_limits_independently(self) -> None:
        # 3 INFO + 3 ERROR at same second; limit 1 per window per severity
        entries = [
            _entry(severity="INFO", ts=_ts(0)),
            _entry(severity="INFO", ts=_ts(0)),
            _entry(severity="INFO", ts=_ts(0)),
            _entry(severity="ERROR", ts=_ts(0)),
            _entry(severity="ERROR", ts=_ts(0)),
            _entry(severity="ERROR", ts=_ts(0)),
        ]
        opts = ThrottleOptions(max_per_window=1, window_seconds=1.0, by_severity=True)
        result = list(throttle_entries(entries, opts))
        assert len(result) == 2
        assert result[0].severity == "INFO"
        assert result[1].severity == "ERROR"

    def test_sliding_window_refills(self) -> None:
        # 2 at t=0, 2 at t=2 with window=1 — second batch should also pass
        entries = [
            _entry(ts=_ts(0)),
            _entry(ts=_ts(0)),
            _entry(ts=_ts(2)),
            _entry(ts=_ts(2)),
        ]
        opts = ThrottleOptions(max_per_window=2, window_seconds=1.0)
        result = list(throttle_entries(entries, opts))
        assert len(result) == 4
