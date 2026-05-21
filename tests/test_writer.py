"""Tests for logslice.writer."""

import io
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from logslice.parser import LogEntry
from logslice.formatter import FormatOptions
from logslice.writer import write_entries, write_lines


DT = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)


def _entry(severity="INFO", message="test"):
    return LogEntry(timestamp=DT, severity=severity, message=message, raw=f"{DT} {severity} {message}")


class TestWriteEntries:
    def test_returns_count_of_written_entries(self, capsys):
        count = write_entries([_entry(), _entry()])
        assert count == 2

    def test_output_goes_to_stdout_by_default(self, capsys):
        write_entries([_entry(message="hello")])
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_writes_to_file(self, tmp_path):
        out = tmp_path / "out.log"
        count = write_entries([_entry(message="file-test")], destination=str(out))
        assert count == 1
        assert "file-test" in out.read_text()

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "sub" / "dir" / "out.log"
        write_entries([_entry()], destination=str(out))
        assert out.exists()

    def test_json_format_produces_json_lines(self, tmp_path):
        import json
        out = tmp_path / "out.json"
        opts = FormatOptions(fmt="json")
        write_entries([_entry()], destination=str(out), options=opts)
        line = out.read_text().strip()
        data = json.loads(line)
        assert "severity" in data

    def test_empty_entries_returns_zero(self, capsys):
        count = write_entries([])
        assert count == 0


class TestWriteLines:
    def test_returns_count(self, capsys):
        count = write_lines(["line one", "line two"])
        assert count == 2

    def test_lines_appear_in_stdout(self, capsys):
        write_lines(["alpha", "beta"])
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "beta" in out

    def test_writes_to_file(self, tmp_path):
        out = tmp_path / "raw.log"
        write_lines(["raw line"], destination=str(out))
        assert "raw line" in out.read_text()

    def test_newline_not_doubled(self, tmp_path):
        out = tmp_path / "nl.log"
        write_lines(["already\n"], destination=str(out))
        content = out.read_text()
        assert content.count("\n") == 1
