"""Tests for logslice.cli_merger."""
from __future__ import annotations

import argparse
import io
import sys
from unittest.mock import patch

import pytest

from logslice.cli_merger import add_merge_subparser, _run_merge
from logslice.merger import MergeOptions


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        files=["-"],
        key="timestamp",
        order="asc",
        tag_source=False,
        output=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestAddMergeSubparser:
    def test_subparser_registered(self):
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers()
        add_merge_subparser(subs)
        args = parser.parse_args(["merge", "a.log", "b.log"])
        assert args.files == ["a.log", "b.log"]

    def test_defaults(self):
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers()
        add_merge_subparser(subs)
        args = parser.parse_args(["merge", "a.log"])
        assert args.key == "timestamp"
        assert args.order == "asc"
        assert args.tag_source is False
        assert args.output is None

    def test_tag_source_flag(self):
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers()
        add_merge_subparser(subs)
        args = parser.parse_args(["merge", "a.log", "--tag-source"])
        assert args.tag_source is True


class TestRunMerge:
    def test_run_merge_with_stdin(self, capsys):
        line = "2024-01-01T00:00:01 INFO hello\n"
        fake_stdin = io.StringIO(line)
        args = _make_args(files=["-"])
        with patch("sys.stdin", fake_stdin):
            rc = _run_merge(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_run_merge_empty_input(self, capsys):
        fake_stdin = io.StringIO("")
        args = _make_args(files=["-"])
        with patch("sys.stdin", fake_stdin):
            rc = _run_merge(args)
        assert rc == 0

    def test_run_merge_two_files(self, tmp_path, capsys):
        f1 = tmp_path / "a.log"
        f2 = tmp_path / "b.log"
        f1.write_text("2024-01-01T00:00:01 INFO alpha\n")
        f2.write_text("2024-01-01T00:00:02 INFO beta\n")
        args = _make_args(files=[str(f1), str(f2)])
        rc = _run_merge(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "alpha" in captured.out
        assert "beta" in captured.out
