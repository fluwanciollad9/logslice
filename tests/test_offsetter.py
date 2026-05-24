"""Tests for logslice.offsetter."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from logslice.offsetter import OffsetOptions, offset_entries
from logslice.parser import LogEntry


_TS = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def _entry(
    message: str = "hello",
    ts: datetime | None = _TS,
    severity: str = "INFO",
) -> LogEntry:
    return LogEntry(timestamp=ts, severity=severity, message=message, raw=message)


# ---------------------------------------------------------------------------
# OffsetOptions validation
# ---------------------------------------------------------------------------

class TestOffsetOptions:
    def test_defaults(self):
        opts = OffsetOptions()
        assert opts.seconds == 0.0
        assert opts.skip_unparsed is True

    def test_non_numeric_seconds_raises(self):
        with pytest.raises(TypeError):
            OffsetOptions(seconds="bad")  # type: ignore[arg-type]

    def test_negative_seconds_accepted(self):
        opts = OffsetOptions(seconds=-3600)
        assert opts.seconds == -3600


# ---------------------------------------------------------------------------
# offset_entries
# ---------------------------------------------------------------------------

class TestOffsetEntries:
    def test_zero_offset_unchanged(self):
        e = _entry()
        result = list(offset_entries([e], OffsetOptions(seconds=0)))
        assert result[0].timestamp == _TS

    def test_positive_offset_shifts_forward(self):
        e = _entry()
        result = list(offset_entries([e], OffsetOptions(seconds=3600)))
        assert result[0].timestamp == _TS + timedelta(hours=1)

    def test_negative_offset_shifts_backward(self):
        e = _entry()
        result = list(offset_entries([e], OffsetOptions(seconds=-60)))
        assert result[0].timestamp == _TS - timedelta(minutes=1)

    def test_message_and_severity_preserved(self):
        e = _entry(message="keep me", severity="ERROR")
        result = list(offset_entries([e], OffsetOptions(seconds=10)))
        assert result[0].message == "keep me"
        assert result[0].severity == "ERROR"

    def test_no_timestamp_skipped_by_default(self):
        e = _entry(ts=None)
        result = list(offset_entries([e]))
        assert len(result) == 1
        assert result[0].timestamp is None

    def test_no_timestamp_dropped_when_skip_false(self):
        e = _entry(ts=None)
        result = list(offset_entries([e], OffsetOptions(skip_unparsed=False)))
        assert result == []

    def test_mixed_entries(self):
        entries = [_entry(ts=_TS), _entry(ts=None), _entry(ts=_TS)]
        opts = OffsetOptions(seconds=30, skip_unparsed=True)
        result = list(offset_entries(entries, opts))
        assert len(result) == 3
        assert result[0].timestamp == _TS + timedelta(seconds=30)
        assert result[1].timestamp is None
        assert result[2].timestamp == _TS + timedelta(seconds=30)

    def test_default_opts_used_when_none_passed(self):
        e = _entry()
        result = list(offset_entries([e]))
        assert result[0].timestamp == _TS

    def test_fractional_seconds(self):
        e = _entry()
        result = list(offset_entries([e], OffsetOptions(seconds=0.5)))
        assert result[0].timestamp == _TS + timedelta(milliseconds=500)
