"""Integration tests: scoper wired into the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.scoper import ScopeOptions


def _entry(severity: str = "INFO", msg: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=msg,
        raw=msg,
    )


def _run(
    entries: list[LogEntry],
    scope: ScopeOptions | None = None,
    min_severity: str = "DEBUG",
) -> list[LogEntry]:
    opts = PipelineOptions(min_severity=min_severity, scope=scope)
    return list(run_pipeline(iter(entries), opts))


class TestPipelineScoper:
    def test_scope_disabled_by_default(self):
        src = [_entry(msg=f"line {i}") for i in range(6)]
        result = _run(src)
        assert len(result) == 6

    def test_scope_applied_after_filter(self):
        # Only ERROR entries survive the severity filter (3 out of 6);
        # scope then keeps the first 2 of those.
        src = [
            _entry("INFO", "a"),
            _entry("ERROR", "b"),
            _entry("INFO", "c"),
            _entry("ERROR", "d"),
            _entry("INFO", "e"),
            _entry("ERROR", "f"),
        ]
        result = _run(src, scope=ScopeOptions(stop=2), min_severity="ERROR")
        assert len(result) == 2
        assert [e.message for e in result] == ["b", "d"]

    def test_scope_step_reduces_output(self):
        src = [_entry(msg=f"line {i}") for i in range(6)]
        result = _run(src, scope=ScopeOptions(step=2))
        assert len(result) == 3
        assert [e.message for e in result] == ["line 0", "line 2", "line 4"]
