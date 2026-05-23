"""Tests for logslice.cli_pager."""
from __future__ import annotations

import argparse
import types
from unittest.mock import MagicMock, patch

import pytest

from logslice.cli_pager import add_page_subparser, _run_page


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        file=None,
        page_size=50,
        page=0,
        all_pages=False,
        min_severity=None,
        color=False,
        func=_run_page,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestAddPageSubparser:
    def _parser(self):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers()
        add_page_subparser(sub)
        return p

    def test_subparser_registered(self):
        p = self._parser()
        ns = p.parse_args(["page"])
        assert hasattr(ns, "func")

    def test_default_page_size(self):
        p = self._parser()
        ns = p.parse_args(["page"])
        assert ns.page_size == 50

    def test_default_page_number(self):
        p = self._parser()
        ns = p.parse_args(["page"])
        assert ns.page == 0

    def test_all_pages_flag(self):
        p = self._parser()
        ns = p.parse_args(["page", "--all-pages"])
        assert ns.all_pages is True

    def test_custom_page_size(self):
        p = self._parser()
        ns = p.parse_args(["page", "--page-size", "20"])
        assert ns.page_size == 20

    def test_min_severity_forwarded(self):
        p = self._parser()
        ns = p.parse_args(["page", "--min-severity", "ERROR"])
        assert ns.min_severity == "ERROR"


class TestRunPage:
    def _fake_entries(self, n=5):
        from datetime import datetime, timezone
        from logslice.parser import LogEntry
        return [
            LogEntry(
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                severity="INFO",
                message=f"msg {i}",
                raw=f"2024-01-01T00:00:00Z INFO msg {i}",
            )
            for i in range(n)
        ]

    def test_returns_zero_on_success(self):
        entries = self._fake_entries(3)
        args = _make_args()
        with patch("logslice.cli_pager.slice_file", return_value=(iter(entries), None)), \
             patch("logslice.cli_pager.write_lines", return_value=3), \
             patch("logslice.cli_pager.sys.stdin"):
            result = _run_page(args)
        assert result == 0

    def test_all_pages_uses_none_page_number(self):
        entries = self._fake_entries(6)
        args = _make_args(all_pages=True, page_size=3)
        captured_opts = {}

        original_page_entries = __import__("logslice.pager", fromlist=["page_entries"]).page_entries

        def fake_page_entries(ents, opts):
            captured_opts["page_number"] = opts.page_number
            return original_page_entries(ents, opts)

        with patch("logslice.cli_pager.slice_file", return_value=(iter(entries), None)), \
             patch("logslice.cli_pager.page_entries", side_effect=fake_page_entries), \
             patch("logslice.cli_pager.write_lines", return_value=0), \
             patch("logslice.cli_pager.sys.stdin"):
            _run_page(args)

        assert captured_opts.get("page_number") is None
