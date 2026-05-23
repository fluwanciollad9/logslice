"""Tests for logslice.pager."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.pager import Page, PageOptions, page_entries, iter_pages


def _entry(msg: str = "hello") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity="INFO",
        message=msg,
        raw=f"2024-01-01T00:00:00Z INFO {msg}",
    )


def _entries(n: int) -> list[LogEntry]:
    return [_entry(f"msg {i}") for i in range(n)]


class TestPageOptions:
    def test_defaults(self):
        opts = PageOptions()
        assert opts.page_size == 50
        assert opts.page_number == 0

    def test_zero_page_size_raises(self):
        with pytest.raises(ValueError, match="page_size"):
            PageOptions(page_size=0)

    def test_negative_page_size_raises(self):
        with pytest.raises(ValueError, match="page_size"):
            PageOptions(page_size=-1)

    def test_negative_page_number_raises(self):
        with pytest.raises(ValueError, match="page_number"):
            PageOptions(page_number=-1)


class TestPageEntries:
    def test_single_full_page(self):
        opts = PageOptions(page_size=3, page_number=0)
        pages = list(page_entries(_entries(3), opts))
        assert len(pages) == 1
        assert pages[0].count() == 3

    def test_two_full_pages(self):
        opts = PageOptions(page_size=3, page_number=None)
        pages = list(page_entries(_entries(6), opts))
        assert len(pages) == 2
        assert pages[0].number == 0
        assert pages[1].number == 1

    def test_trailing_partial_page(self):
        opts = PageOptions(page_size=3, page_number=None)
        pages = list(page_entries(_entries(5), opts))
        assert len(pages) == 2
        assert pages[-1].count() == 2

    def test_specific_page_returned(self):
        opts = PageOptions(page_size=2, page_number=1)
        pages = list(page_entries(_entries(6), opts))
        assert len(pages) == 1
        assert pages[0].number == 1

    def test_page_beyond_data_returns_nothing(self):
        opts = PageOptions(page_size=10, page_number=5)
        pages = list(page_entries(_entries(3), opts))
        assert pages == []

    def test_empty_input_yields_no_pages(self):
        opts = PageOptions(page_size=5, page_number=None)
        assert list(page_entries([], opts)) == []

    def test_page_entries_messages_preserved(self):
        entries = _entries(4)
        opts = PageOptions(page_size=4, page_number=0)
        pages = list(page_entries(entries, opts))
        assert [e.message for e in pages[0].entries] == [f"msg {i}" for i in range(4)]

    def test_default_options_used_when_none(self):
        # Should not raise; uses PageOptions() defaults
        pages = list(page_entries(_entries(10)))
        assert pages[0].count() == 10  # page_number=0, size=50
