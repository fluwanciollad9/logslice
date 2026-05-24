"""Tests for logslice.labeler."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.labeler import LabelOptions, label_entry, label_entries


def _entry(message: str = "hello", tags: dict | None = None) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity="INFO",
        message=message,
        raw=f"2024-01-01T00:00:00Z INFO {message}",
        tags=tags or {},
    )


class TestLabelOptions:
    def test_defaults(self):
        opts = LabelOptions()
        assert opts.labels == {}
        assert opts.overwrite is True

    def test_non_dict_labels_raises(self):
        with pytest.raises(TypeError):
            LabelOptions(labels=["env=prod"])

    def test_empty_key_raises(self):
        with pytest.raises(ValueError):
            LabelOptions(labels={"": "val"})

    def test_non_string_value_raises(self):
        with pytest.raises(TypeError):
            LabelOptions(labels={"env": 42})

    def test_valid_labels_accepted(self):
        opts = LabelOptions(labels={"env": "prod", "region": "us-east"})
        assert opts.labels["env"] == "prod"


class TestLabelEntry:
    def test_no_labels_returns_same_entry(self):
        e = _entry()
        result = label_entry(e, LabelOptions())
        assert result is e

    def test_label_added_to_empty_tags(self):
        e = _entry()
        result = label_entry(e, LabelOptions(labels={"env": "prod"}))
        assert result.tags["env"] == "prod"

    def test_existing_tag_overwritten_when_overwrite_true(self):
        e = _entry(tags={"env": "dev"})
        result = label_entry(e, LabelOptions(labels={"env": "prod"}, overwrite=True))
        assert result.tags["env"] == "prod"

    def test_existing_tag_preserved_when_overwrite_false(self):
        e = _entry(tags={"env": "dev"})
        result = label_entry(e, LabelOptions(labels={"env": "prod"}, overwrite=False))
        assert result.tags["env"] == "dev"

    def test_new_label_added_even_when_overwrite_false(self):
        e = _entry(tags={"env": "dev"})
        result = label_entry(e, LabelOptions(labels={"region": "eu"}, overwrite=False))
        assert result.tags["region"] == "eu"
        assert result.tags["env"] == "dev"

    def test_original_entry_not_mutated(self):
        original_tags = {"env": "dev"}
        e = _entry(tags=original_tags)
        label_entry(e, LabelOptions(labels={"env": "prod"}))
        assert original_tags["env"] == "dev"

    def test_other_fields_preserved(self):
        e = _entry(message="test msg")
        result = label_entry(e, LabelOptions(labels={"k": "v"}))
        assert result.message == "test msg"
        assert result.severity == "INFO"
        assert result.timestamp == e.timestamp


class TestLabelEntries:
    def test_yields_all_entries(self):
        entries = [_entry("a"), _entry("b"), _entry("c")]
        result = list(label_entries(entries, LabelOptions(labels={"x": "1"})))
        assert len(result) == 3

    def test_all_entries_labeled(self):
        entries = [_entry(), _entry()]
        result = list(label_entries(entries, LabelOptions(labels={"src": "test"})))
        assert all(e.tags.get("src") == "test" for e in result)

    def test_empty_input_yields_nothing(self):
        result = list(label_entries([], LabelOptions(labels={"k": "v"})))
        assert result == []
