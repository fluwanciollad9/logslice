"""Tests for logslice.formatter."""

import json
from datetime import datetime, timezone

import pytest

from logslice.parser import LogEntry
from logslice.formatter import FormatOptions, format_entry, format_entries


DT = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)


def _entry(severity="INFO", message="hello world"):
    return LogEntry(timestamp=DT, severity=severity, message=message, raw=f"{DT} {severity} {message}")


class TestFormatEntryText:
    def test_default_format_contains_timestamp(self):
        result = format_entry(_entry())
        assert "2024-03-15" in result

    def test_default_format_contains_severity(self):
        result = format_entry(_entry(severity="ERROR"))
        assert "ERROR" in result

    def test_default_format_contains_message(self):
        result = format_entry(_entry(message="disk full"))
        assert "disk full" in result

    def test_show_source_prepends_filename(self):
        opts = FormatOptions(show_source=True)
        result = format_entry(_entry(), options=opts, source="app.log")
        assert "[app.log]" in result

    def test_no_source_when_show_source_false(self):
        opts = FormatOptions(show_source=False)
        result = format_entry(_entry(), options=opts, source="app.log")
        assert "app.log" not in result

    def test_color_wraps_severity_with_ansi(self):
        opts = FormatOptions(color=True)
        result = format_entry(_entry(severity="WARNING"), options=opts)
        assert "\033[" in result
        assert "WARNING" in result


class TestFormatEntryJson:
    def test_returns_valid_json(self):
        opts = FormatOptions(fmt="json")
        result = format_entry(_entry(), options=opts)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_json_has_required_keys(self):
        opts = FormatOptions(fmt="json")
        data = json.loads(format_entry(_entry(), options=opts))
        assert {"timestamp", "severity", "message"} <= data.keys()

    def test_json_source_included_when_requested(self):
        opts = FormatOptions(fmt="json", show_source=True)
        data = json.loads(format_entry(_entry(), options=opts, source="srv.log"))
        assert data["source"] == "srv.log"

    def test_json_source_absent_when_not_requested(self):
        opts = FormatOptions(fmt="json", show_source=False)
        data = json.loads(format_entry(_entry(), options=opts, source="srv.log"))
        assert "source" not in data

    def test_json_timestamp_is_iso_format(self):
        opts = FormatOptions(fmt="json")
        data = json.loads(format_entry(_entry(), options=opts))
        # Should be parseable as an ISO 8601 datetime string
        parsed = datetime.fromisoformat(data["timestamp"])
        assert parsed.year == DT.year
        assert parsed.month == DT.month
        assert parsed.day == DT.day


class TestFormatEntryCsv:
    def test_returns_three_columns_by_default(self):
        opts = FormatOptions(fmt="csv")
        result = format_entry(_entry(), options=opts)
        assert result.count(",") >= 2

    def test_message_present_in_csv(self):
        opts = FormatOptions(fmt="csv")
        result = format_entry(_entry(message="test msg"), options=opts)
        assert "test msg" in result


class TestFormatEntries:
    def test_returns_same_count(self):
        entries = [_entry(), _entry(severity="ERROR"), _entry(severity="WARNING")]
        results = list(format_entries(entries))
        assert len(results) == len(entries)

    def test_empty_input_returns_empty(self):
        results = list(format_entries([]))
        assert results == []
