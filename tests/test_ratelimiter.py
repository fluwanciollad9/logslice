"""Tests for logslice.ratelimiter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.parser import LogEntry
from logslice.ratelimiter import RateLimitOptions, ratelimit_entries


def _entry(message: str, ts_offset_seconds: float = 0.0, severity: str = "INFO") -> LogEntry:
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta

    return LogEntry(
        timestamp=base + timedelta(seconds=ts_offset_seconds),
        severity=severity,
        message=message,
        raw=f"2024-01-01T12:00:00 {severity} {message}",
    )


def _no_ts(message: str) -> LogEntry:
    return LogEntry(timestamp=None, severity="INFO", message=message, raw=message)


class TestRateLimitOptions:
    def test_defaults(self):
        opts = RateLimitOptions()
        assert opts.window_seconds == 60.0
        assert opts.max_per_window == 5

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitOptions(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitOptions(window_seconds=-1)

    def test_zero_max_raises(self):
        with pytest.raises(ValueError, match="max_per_window"):
            RateLimitOptions(max_per_window=0)


class TestRatelimitEntries:
    def test_none_options_passes_all(self):
        entries = [_entry("msg", i) for i in range(10)]
        result = list(ratelimit_entries(iter(entries), options=None))
        assert result == entries

    def test_entries_without_timestamp_always_pass(self):
        entries = [_no_ts("bare line")] * 20
        opts = RateLimitOptions(window_seconds=60, max_per_window=1)
        result = list(ratelimit_entries(iter(entries), opts))
        assert len(result) == 20

    def test_first_entry_always_passes(self):
        opts = RateLimitOptions(window_seconds=60, max_per_window=3)
        result = list(ratelimit_entries(iter([_entry("hello", 0)]), opts))
        assert len(result) == 1

    def test_suppresses_excess_within_window(self):
        opts = RateLimitOptions(window_seconds=60, max_per_window=2)
        entries = [_entry("same", i) for i in range(5)]
        result = list(ratelimit_entries(iter(entries), opts))
        assert len(result) == 2

    def test_resets_after_window_expires(self):
        opts = RateLimitOptions(window_seconds=10, max_per_window=2)
        # 2 within first window, then 2 more after window expires
        entries = [_entry("msg", 0), _entry("msg", 1), _entry("msg", 2),
                   _entry("msg", 15), _entry("msg", 16), _entry("msg", 17)]
        result = list(ratelimit_entries(iter(entries), opts))
        assert len(result) == 4

    def test_different_messages_tracked_independently(self):
        opts = RateLimitOptions(window_seconds=60, max_per_window=1)
        entries = [_entry("alpha", 0), _entry("beta", 1), _entry("alpha", 2)]
        result = list(ratelimit_entries(iter(entries), opts))
        # alpha suppressed at t=2, beta passes
        assert len(result) == 2
        assert result[0].message == "alpha"
        assert result[1].message == "beta"

    def test_different_severities_tracked_independently(self):
        opts = RateLimitOptions(window_seconds=60, max_per_window=1)
        entries = [_entry("msg", 0, "INFO"), _entry("msg", 1, "ERROR")]
        result = list(ratelimit_entries(iter(entries), opts))
        assert len(result) == 2
