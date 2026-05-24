"""Tests for logslice.capper."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.capper import CapOptions, cap_entries
from logslice.parser import LogEntry


def _entry(severity: str, message: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=f"{severity} {message}",
    )


def _entries(severities: list[str]) -> list[LogEntry]:
    return [_entry(s, f"message {i}") for i, s in enumerate(severities)]


# ---------------------------------------------------------------------------
# CapOptions validation
# ---------------------------------------------------------------------------

class TestCapOptions:
    def test_defaults(self):
        opts = CapOptions()
        assert opts.max_per_severity == 0
        assert opts.severities == []

    def test_negative_max_raises(self):
        with pytest.raises(ValueError, match="max_per_severity"):
            CapOptions(max_per_severity=-1)

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Unknown severity"):
            CapOptions(max_per_severity=1, severities=["VERBOSE"])

    def test_severities_normalised_to_upper(self):
        opts = CapOptions(max_per_severity=2, severities=["error", "Warning"])
        assert opts.severities == ["ERROR", "WARNING"]


# ---------------------------------------------------------------------------
# cap_entries behaviour
# ---------------------------------------------------------------------------

class TestCapEntries:
    def test_none_opts_passes_all(self):
        entries = _entries(["INFO", "INFO", "INFO"])
        result = list(cap_entries(entries, opts=None))
        assert len(result) == 3

    def test_zero_max_passes_all(self):
        entries = _entries(["ERROR", "ERROR", "ERROR"])
        result = list(cap_entries(entries, CapOptions(max_per_severity=0)))
        assert len(result) == 3

    def test_cap_limits_per_severity(self):
        entries = _entries(["INFO", "INFO", "INFO", "ERROR", "ERROR"])
        opts = CapOptions(max_per_severity=2)
        result = list(cap_entries(entries, opts))
        info_count = sum(1 for e in result if e.severity == "INFO")
        error_count = sum(1 for e in result if e.severity == "ERROR")
        assert info_count == 2
        assert error_count == 2

    def test_cap_only_targeted_severities(self):
        entries = _entries(["DEBUG", "DEBUG", "DEBUG", "INFO", "INFO", "INFO"])
        opts = CapOptions(max_per_severity=1, severities=["DEBUG"])
        result = list(cap_entries(entries, opts))
        debug_count = sum(1 for e in result if e.severity == "DEBUG")
        info_count = sum(1 for e in result if e.severity == "INFO")
        assert debug_count == 1
        assert info_count == 3  # uncapped

    def test_mixed_severities_each_capped_independently(self):
        sevs = ["ERROR"] * 5 + ["WARNING"] * 5 + ["INFO"] * 5
        opts = CapOptions(max_per_severity=3)
        result = list(cap_entries(_entries(sevs), opts))
        assert len(result) == 9

    def test_unknown_severity_in_stream_treated_as_unknown(self):
        entries = [_entry("TRACE", f"m{i}") for i in range(4)]
        opts = CapOptions(max_per_severity=2)
        result = list(cap_entries(entries, opts))
        assert len(result) == 2
