"""Tests for logslice.transformer."""
from datetime import datetime, timezone

import pytest

from logslice.parser import LogEntry
from logslice.transformer import TransformOptions, transform_entries, transform_entry

_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _entry(
    message: str = "hello world",
    severity: str = "INFO",
    source: str | None = "app",
    tags: set[str] | None = None,
) -> LogEntry:
    return LogEntry(
        timestamp=_TS,
        severity=severity,
        message=message,
        source=source,
        raw=f"{severity} {message}",
        tags=tags or set(),
    )


class TestTransformOptions:
    def test_defaults_are_empty(self):
        opts = TransformOptions()
        assert opts.message_transforms == []
        assert opts.severity_transforms == []
        assert opts.source_transforms == []
        assert opts.drop_fields == set()

    def test_unknown_drop_field_raises(self):
        with pytest.raises(ValueError, match="Unknown drop_fields"):
            TransformOptions(drop_fields={"nonexistent"})

    def test_valid_drop_fields_accepted(self):
        opts = TransformOptions(drop_fields={"message", "tags"})
        assert "message" in opts.drop_fields


class TestTransformEntry:
    def test_message_transform_applied(self):
        opts = TransformOptions(message_transforms=[str.upper])
        result = transform_entry(_entry(message="hello"), opts)
        assert result.message == "HELLO"

    def test_multiple_message_transforms_chained(self):
        opts = TransformOptions(
            message_transforms=[str.upper, lambda s: s.replace("O", "0")]
        )
        result = transform_entry(_entry(message="foo"), opts)
        assert result.message == "F00"

    def test_severity_transform_applied(self):
        opts = TransformOptions(severity_transforms=[str.lower])
        result = transform_entry(_entry(severity="ERROR"), opts)
        assert result.severity == "error"

    def test_source_transform_applied(self):
        opts = TransformOptions(source_transforms=[str.upper])
        result = transform_entry(_entry(source="app"), opts)
        assert result.source == "APP"

    def test_source_none_stays_none(self):
        opts = TransformOptions(source_transforms=[str.upper])
        result = transform_entry(_entry(source=None), opts)
        assert result.source is None

    def test_drop_message_field(self):
        opts = TransformOptions(drop_fields={"message"})
        result = transform_entry(_entry(message="secret"), opts)
        assert result.message == ""

    def test_drop_tags_field(self):
        opts = TransformOptions(drop_fields={"tags"})
        result = transform_entry(_entry(tags={"debug", "verbose"}), opts)
        assert result.tags == set()

    def test_drop_source_field(self):
        opts = TransformOptions(drop_fields={"source"})
        result = transform_entry(_entry(source="myapp"), opts)
        assert result.source is None

    def test_timestamp_preserved(self):
        opts = TransformOptions(message_transforms=[str.upper])
        result = transform_entry(_entry(), opts)
        assert result.timestamp == _TS

    def test_original_entry_not_mutated(self):
        original = _entry(message="original", tags={"keep"})
        opts = TransformOptions(
            message_transforms=[str.upper], drop_fields={"tags"}
        )
        transform_entry(original, opts)
        assert original.message == "original"
        assert original.tags == {"keep"}


class TestTransformEntries:
    def test_yields_all_entries(self):
        entries = [_entry(message=f"msg{i}") for i in range(5)]
        opts = TransformOptions()
        results = list(transform_entries(entries, opts))
        assert len(results) == 5

    def test_transform_applied_to_all(self):
        entries = [_entry(message="hello"), _entry(message="world")]
        opts = TransformOptions(message_transforms=[str.upper])
        results = list(transform_entries(entries, opts))
        assert all(r.message == r.message.upper() for r in results)

    def test_empty_input_yields_nothing(self):
        opts = TransformOptions()
        assert list(transform_entries([], opts)) == []
