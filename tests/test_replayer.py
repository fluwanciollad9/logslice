"""Tests for logslice.replayer."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from logslice.parser import LogEntry
from logslice.replayer import ReplayOptions, replay_entries


def _entry(offset_s: float = 0.0, msg: str = "hello") -> LogEntry:
    ts = datetime.fromtimestamp(1_700_000_000 + offset_s, tz=timezone.utc)
    return LogEntry(timestamp=ts, severity="INFO", message=msg, raw=msg)


# ---------------------------------------------------------------------------
# ReplayOptions validation
# ---------------------------------------------------------------------------

class TestReplayOptions:
    def test_defaults(self):
        o = ReplayOptions()
        assert o.speed == 1.0
        assert o.real_time is True
        assert o.max_delay == 5.0

    def test_zero_speed_raises(self):
        with pytest.raises(ValueError, match="speed"):
            ReplayOptions(speed=0)

    def test_negative_speed_raises(self):
        with pytest.raises(ValueError, match="speed"):
            ReplayOptions(speed=-1)

    def test_negative_max_delay_raises(self):
        with pytest.raises(ValueError, match="max_delay"):
            ReplayOptions(max_delay=-0.1)

    def test_zero_max_delay_allowed(self):
        o = ReplayOptions(max_delay=0)
        assert o.max_delay == 0


# ---------------------------------------------------------------------------
# replay_entries behaviour
# ---------------------------------------------------------------------------

class TestReplayEntries:
    def test_all_entries_yielded(self):
        entries = [_entry(i) for i in range(5)]
        result = list(replay_entries(entries, ReplayOptions(real_time=False)))
        assert len(result) == 5

    def test_no_sleep_when_real_time_false(self):
        entries = [_entry(i * 2) for i in range(4)]
        with patch("logslice.replayer.time.sleep") as mock_sleep:
            list(replay_entries(entries, ReplayOptions(real_time=False)))
        mock_sleep.assert_not_called()

    def test_sleep_called_between_entries(self):
        entries = [_entry(0), _entry(2), _entry(4)]
        with patch("logslice.replayer.time.sleep") as mock_sleep:
            list(replay_entries(entries, ReplayOptions(real_time=True, speed=1.0)))
        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert abs(call.args[0] - 2.0) < 1e-6

    def test_speed_divides_gap(self):
        entries = [_entry(0), _entry(4)]
        with patch("logslice.replayer.time.sleep") as mock_sleep:
            list(replay_entries(entries, ReplayOptions(real_time=True, speed=2.0)))
        assert abs(mock_sleep.call_args.args[0] - 2.0) < 1e-6

    def test_gap_capped_by_max_delay(self):
        entries = [_entry(0), _entry(100)]
        opts = ReplayOptions(real_time=True, speed=1.0, max_delay=3.0)
        with patch("logslice.replayer.time.sleep") as mock_sleep:
            list(replay_entries(entries, opts))
        assert mock_sleep.call_args.args[0] == 3.0

    def test_entry_without_timestamp_skips_sleep(self):
        e1 = _entry(0)
        e2 = LogEntry(timestamp=None, severity="INFO", message="no ts", raw="no ts")
        e3 = _entry(5)
        with patch("logslice.replayer.time.sleep") as mock_sleep:
            list(replay_entries([e1, e2, e3], ReplayOptions(real_time=True)))
        # Only one sleep: between e2 (no ts, skipped) and e3 prev_ts stays at e1
        assert mock_sleep.call_count == 1

    def test_default_options_used_when_none(self):
        entries = [_entry(0)]
        with patch("logslice.replayer.time.sleep"):
            result = list(replay_entries(entries))
        assert len(result) == 1

    def test_empty_input_yields_nothing(self):
        result = list(replay_entries([], ReplayOptions(real_time=False)))
        assert result == []
