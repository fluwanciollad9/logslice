"""Integration tests: replayer inside the pipeline (real_time=False)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from logslice.parser import LogEntry
from logslice.pipeline import PipelineOptions, run_pipeline
from logslice.replayer import ReplayOptions


def _entry(offset_s: float = 0.0, severity: str = "INFO") -> LogEntry:
    ts = datetime.fromtimestamp(1_700_000_000 + offset_s, tz=timezone.utc)
    return LogEntry(timestamp=ts, severity=severity, message="msg", raw="msg")


def _run(entries, severity=None, replay: ReplayOptions | None = None):
    opts = PipelineOptions(
        min_severity=severity,
        replay=replay,
    )
    return list(run_pipeline(entries, opts))


class TestPipelineReplayer:
    def test_replay_disabled_by_default_passes_all(self):
        entries = [_entry(i) for i in range(4)]
        result = _run(entries)
        assert len(result) == 4

    def test_only_filtered_entries_are_replayed(self):
        entries = [_entry(0, "DEBUG"), _entry(1, "ERROR"), _entry(2, "INFO")]
        result = _run(entries, severity="ERROR", replay=ReplayOptions(real_time=False))
        assert len(result) == 1
        assert result[0].severity == "ERROR"

    def test_no_sleep_during_pipeline_dry_run(self):
        entries = [_entry(i * 3) for i in range(5)]
        with patch("logslice.replayer.time.sleep") as mock_sleep:
            _run(entries, replay=ReplayOptions(real_time=False))
        mock_sleep.assert_not_called()

    def test_order_preserved_through_replay(self):
        entries = [_entry(i, "WARNING") for i in range(6)]
        result = _run(entries, replay=ReplayOptions(real_time=False))
        timestamps = [e.timestamp for e in result]
        assert timestamps == sorted(timestamps)
