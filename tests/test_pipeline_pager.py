"""Integration tests: pager wired through the pipeline."""
from __future__ import annotations

from datetime import datetime, timezone

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.pager import PageOptions, page_entries


def _entry(severity: str = "INFO", msg: str = "hello") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        severity=severity,
        message=msg,
        raw=f"2024-01-01T00:00:00Z {severity} {msg}",
    )


def _run(entries, filter_opts=None, page_opts=None):
    filtered = filter_entries(entries, filter_opts or FilterOptions())
    return list(page_entries(filtered, page_opts or PageOptions(page_size=50, page_number=None)))


class TestPipelinePager:
    def test_pager_disabled_by_default_passes_all(self):
        entries = [_entry() for _ in range(10)]
        pages = _run(entries)
        total = sum(p.count() for p in pages)
        assert total == 10

    def test_only_filtered_entries_are_paged(self):
        entries = [_entry("ERROR")] * 3 + [_entry("DEBUG")] * 7
        fopts = FilterOptions(min_severity="ERROR")
        pages = _run(entries, filter_opts=fopts, page_opts=PageOptions(page_size=50, page_number=None))
        total = sum(p.count() for p in pages)
        assert total == 3

    def test_page_size_splits_correctly(self):
        entries = [_entry() for _ in range(25)]
        pages = _run(entries, page_opts=PageOptions(page_size=10, page_number=None))
        assert len(pages) == 3
        assert pages[0].count() == 10
        assert pages[1].count() == 10
        assert pages[2].count() == 5

    def test_select_second_page(self):
        entries = [_entry(msg=f"m{i}") for i in range(20)]
        pages = _run(entries, page_opts=PageOptions(page_size=5, page_number=2))
        assert len(pages) == 1
        assert pages[0].number == 2
        assert [e.message for e in pages[0].entries] == [f"m{i}" for i in range(10, 15)]
