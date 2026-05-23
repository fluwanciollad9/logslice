"""Tests for logslice.clamper."""
from __future__ import annotations

import pytest
from datetime import datetime

from logslice.parser import LogEntry
from logslice.clamper import ClampOptions, clamp_entries


def _entry(severity: str, message: str = "msg") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
        raw=f"2024-01-01 12:00:00 {severity.upper()} {message}",
    )


class TestClampOptions:
    def test_defaults_allow_everything(self) -> None:
        opts = ClampOptions()
        assert opts.min_severity is None
        assert opts.max_severity is None
        assert opts.allowed_severities == []

    def test_invalid_min_severity_raises(self) -> None:
        with pytest.raises(ValueError, match="min_severity"):
            ClampOptions(min_severity="verbose")

    def test_invalid_max_severity_raises(self) -> None:
        with pytest.raises(ValueError, match="max_severity"):
            ClampOptions(max_severity="fatal")

    def test_min_above_max_raises(self) -> None:
        with pytest.raises(ValueError, match="min_severity must not be higher"):
            ClampOptions(min_severity="error", max_severity="info")

    def test_equal_min_max_is_valid(self) -> None:
        opts = ClampOptions(min_severity="warning", max_severity="warning")
        assert opts.min_severity == "warning"
        assert opts.max_severity == "warning"

    def test_severities_normalised_to_lowercase(self) -> None:
        opts = ClampOptions(min_severity="INFO", max_severity="ERROR")
        assert opts.min_severity == "info"
        assert opts.max_severity == "error"


class TestClampEntries:
    def _run(self, entries, **kwargs):
        opts = ClampOptions(**kwargs) if kwargs else None
        return list(clamp_entries(entries, opts))

    def test_no_opts_passes_all_entries(self) -> None:
        entries = [_entry("debug"), _entry("info"), _entry("error")]
        assert self._run(entries) == entries

    def test_min_severity_filters_below(self) -> None:
        entries = [_entry("debug"), _entry("info"), _entry("warning"), _entry("error")]
        result = self._run(entries, min_severity="warning")
        severities = [e.severity for e in result]
        assert severities == ["warning", "error"]

    def test_max_severity_filters_above(self) -> None:
        entries = [_entry("info"), _entry("warning"), _entry("error"), _entry("critical")]
        result = self._run(entries, max_severity="warning")
        severities = [e.severity for e in result]
        assert severities == ["info", "warning"]

    def test_min_and_max_combined(self) -> None:
        entries = [
            _entry("debug"),
            _entry("info"),
            _entry("warning"),
            _entry("error"),
            _entry("critical"),
        ]
        result = self._run(entries, min_severity="info", max_severity="error")
        severities = [e.severity for e in result]
        assert severities == ["info", "warning", "error"]

    def test_empty_entries_returns_empty(self) -> None:
        assert self._run([]) == []

    def test_allowed_severities_filters_to_exact_set(self) -> None:
        entries = [
            _entry("debug"),
            _entry("info"),
            _entry("warning"),
            _entry("error"),
        ]
        result = self._run(entries, allowed_severities=["info", "error"])
        severities = [e.severity for e in result]
        assert severities == ["info", "error"]
