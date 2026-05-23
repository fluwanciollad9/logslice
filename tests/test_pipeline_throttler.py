"""Integration tests: throttler wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.throttler import ThrottleOptions


def _entry(
    msg: str = "msg",
    severity: str = "ERROR",
    second: int = 0,
) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc),
        severity=severity,
        message=msg,
        raw=f"2024-01-01T00:00:{second:02d}Z {severity} {msg}",
    )


def _run(entries: list[LogEntry], throttle: ThrottleOptions) -> list[LogEntry]:
    opts = PipelineOptions(throttle=throttle)
    return list(run_pipeline(iter(entries), opts))


class TestPipelineThrottler:
    def test_throttle_disabled_by_default(self) -> None:
        entries = [_entry(second=0) for _ in range(10)]
        opts = PipelineOptions()
        result = list(run_pipeline(iter(entries), opts))
        assert len(result) == 10

    def test_throttle_reduces_output(self) -> None:
        entries = [_entry(second=0) for _ in range(8)]
        result = _run(entries, ThrottleOptions(max_per_window=2, window_seconds=1.0))
        assert len(result) == 2

    def test_throttle_after_filter(self) -> None:
        # mix of INFO and ERROR; pipeline filters to ERROR, then throttles
        entries = [
            _entry(severity="INFO", second=0),
            _entry(severity="ERROR", second=0),
            _entry(severity="ERROR", second=0),
            _entry(severity="ERROR", second=0),
        ]
        from logslice.filter import FilterOptions
        opts = PipelineOptions(
            filter=FilterOptions(min_severity="ERROR"),
            throttle=ThrottleOptions(max_per_window=1, window_seconds=1.0),
        )
        result = list(run_pipeline(iter(entries), opts))
        # Only ERROR entries reach throttler; throttler allows 1
        assert len(result) == 1
        assert result[0].severity == "ERROR"
