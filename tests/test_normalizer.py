"""Tests for logslice.normalizer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.parser import LogEntry
from logslice.normalizer import NormalizeOptions, normalize_entry, normalize_entries


def _entry(
    severity: str = "info",
    message: str = "hello world",
    source: str | None = None,
) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        source=source,
        raw=f"2024-01-01T12:00:00Z {severity} {message}",
        tags={},
    )


class TestNormalizeOptions:
    def test_defaults(self):
        opts = NormalizeOptions()
        assert opts.severity is True
        assert opts.strip_message is True
        assert opts.uppercase_source is False
        assert opts.extra_severity_map == {}

    def test_empty_extra_key_raises(self):
        with pytest.raises(ValueError, match="keys must be non-empty"):
            NormalizeOptions(extra_severity_map={"": "INFO"})

    def test_empty_extra_value_raises(self):
        with pytest.raises(ValueError, match="values must be non-empty"):
            NormalizeOptions(extra_severity_map={"notice": ""})


class TestNormalizeSeverity:
    def test_warn_becomes_warning(self):
        result = normalize_entry(_entry(severity="warn"), NormalizeOptions())
        assert result.severity == "WARNING"

    def test_err_becomes_error(self):
        result = normalize_entry(_entry(severity="err"), NormalizeOptions())
        assert result.severity == "ERROR"

    def test_fatal_becomes_critical(self):
        result = normalize_entry(_entry(severity="fatal"), NormalizeOptions())
        assert result.severity == "CRITICAL"

    def test_trace_becomes_debug(self):
        result = normalize_entry(_entry(severity="trace"), NormalizeOptions())
        assert result.severity == "DEBUG"

    def test_unknown_severity_uppercased(self):
        result = normalize_entry(_entry(severity="notice"), NormalizeOptions())
        assert result.severity == "NOTICE"

    def test_severity_disabled_leaves_value_unchanged(self):
        result = normalize_entry(_entry(severity="warn"), NormalizeOptions(severity=False))
        assert result.severity == "warn"

    def test_extra_severity_map_applied(self):
        opts = NormalizeOptions(extra_severity_map={"notice": "INFO"})
        result = normalize_entry(_entry(severity="notice"), opts)
        assert result.severity == "INFO"


class TestNormalizeMessage:
    def test_strip_message_removes_whitespace(self):
        result = normalize_entry(_entry(message="  padded  "), NormalizeOptions())
        assert result.message == "padded"

    def test_strip_disabled_preserves_whitespace(self):
        result = normalize_entry(
            _entry(message="  padded  "), NormalizeOptions(strip_message=False)
        )
        assert result.message == "  padded  "


class TestNormalizeSource:
    def test_uppercase_source_when_enabled(self):
        result = normalize_entry(
            _entry(source="myapp"), NormalizeOptions(uppercase_source=True)
        )
        assert result.source == "MYAPP"

    def test_source_unchanged_when_disabled(self):
        result = normalize_entry(
            _entry(source="myapp"), NormalizeOptions(uppercase_source=False)
        )
        assert result.source == "myapp"

    def test_none_source_stays_none(self):
        result = normalize_entry(_entry(source=None), NormalizeOptions(uppercase_source=True))
        assert result.source is None


class TestNormalizeEntries:
    def test_yields_all_entries(self):
        entries = [_entry(), _entry(severity="warn"), _entry(severity="err")]
        result = list(normalize_entries(entries))
        assert len(result) == 3

    def test_default_opts_used_when_none(self):
        entries = [_entry(severity="warn")]
        result = list(normalize_entries(entries))
        assert result[0].severity == "WARNING"

    def test_tags_preserved(self):
        e = _entry()
        e.tags["env"] = "prod"
        result = normalize_entry(e, NormalizeOptions())
        assert result.tags == {"env": "prod"}
