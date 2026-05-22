"""Integration tests: rate limiter wired through the pipeline."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.ratelimiter import RateLimitOptions

_BASE = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _entry(msg: str, offset: float, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=_BASE + timedelta(seconds=offset),
        severity=severity,
        message=msg,
        raw=f"{severity} {msg}",
    )


def _run(entries, ratelimit=None):
    opts = PipelineOptions(ratelimit=ratelimit)
    return list(run_pipeline(iter(entries), opts))


class TestPipelineRatelimiter:
    def test_ratelimit_disabled_by_default(self):
        entries = [_entry("flood", i) for i in range(20)]
        result = _run(entries)
        assert len(result) == 20

    def test_ratelimit_reduces_output(self):
        opts = RateLimitOptions(window_seconds=60, max_per_window=3)
        entries = [_entry("repeat", i) for i in range(10)]
        result = _run(entries, ratelimit=opts)
        assert len(result) == 3

    def test_ratelimit_passes_distinct_messages(self):
        opts = RateLimitOptions(window_seconds=60, max_per_window=1)
        entries = [_entry(f"msg-{i}", i) for i in range(5)]
        result = _run(entries, ratelimit=opts)
        assert len(result) == 5

    def test_ratelimit_interacts_with_severity_filter(self):
        from logslice.filter import FilterOptions

        rl_opts = RateLimitOptions(window_seconds=60, max_per_window=2)
        entries = (
            [_entry("boom", i, "ERROR") for i in range(5)]
            + [_entry("info msg", i + 10, "INFO") for i in range(5)]
        )
        pipe_opts = PipelineOptions(
            filter=FilterOptions(min_severity="ERROR"),
            ratelimit=rl_opts,
        )
        result = list(run_pipeline(iter(entries), pipe_opts))
        # Only ERROR entries pass the filter; then rate-limited to 2
        assert len(result) == 2
        assert all(e.severity == "ERROR" for e in result)
