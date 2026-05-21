"""Tests for logslice.sampler."""

from __future__ import annotations

import datetime
import pytest

from logslice.parser import LogEntry
from logslice.sampler import SampleOptions, sample_entries


def _entry(msg: str = "hello") -> LogEntry:
    return LogEntry(
        raw=msg,
        timestamp=datetime.datetime(2024, 1, 1, 12, 0, 0),
        severity="INFO",
        message=msg,
    )


def _entries(n: int) -> list[LogEntry]:
    return [_entry(f"msg-{i}") for i in range(n)]


class TestSampleOptions:
    def test_default_keeps_all(self) -> None:
        opts = SampleOptions()
        assert opts.rate == 1
        assert opts.reservoir_size is None

    def test_invalid_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="rate"):
            SampleOptions(rate=0)

    def test_invalid_reservoir_raises(self) -> None:
        with pytest.raises(ValueError, match="reservoir_size"):
            SampleOptions(reservoir_size=0)


class TestSampleEntries:
    def test_rate_one_yields_all(self) -> None:
        entries = _entries(10)
        result = list(sample_entries(entries, SampleOptions(rate=1)))
        assert len(result) == 10

    def test_rate_two_halves_output(self) -> None:
        entries = _entries(20)
        result = list(sample_entries(entries, SampleOptions(rate=2, seed=42)))
        assert len(result) == 10

    def test_rate_three_rounds_up_remainder(self) -> None:
        # 10 entries / rate 3 → 3 full buckets + 1 remainder = 4 entries
        entries = _entries(10)
        result = list(sample_entries(entries, SampleOptions(rate=3, seed=0)))
        assert len(result) == 4

    def test_reservoir_exact_size(self) -> None:
        entries = _entries(50)
        result = list(sample_entries(entries, SampleOptions(reservoir_size=10, seed=7)))
        assert len(result) == 10

    def test_reservoir_smaller_than_input(self) -> None:
        entries = _entries(5)
        result = list(sample_entries(entries, SampleOptions(reservoir_size=10, seed=1)))
        # Cannot return more entries than available.
        assert len(result) == 5

    def test_reservoir_reproducible_with_seed(self) -> None:
        entries = _entries(100)
        opts = SampleOptions(reservoir_size=20, seed=99)
        first = [e.message for e in sample_entries(entries, opts)]
        second = [e.message for e in sample_entries(entries, opts)]
        assert first == second

    def test_rate_reproducible_with_seed(self) -> None:
        entries = _entries(30)
        opts = SampleOptions(rate=3, seed=55)
        first = [e.message for e in sample_entries(entries, opts)]
        second = [e.message for e in sample_entries(entries, opts)]
        assert first == second

    def test_empty_input_yields_nothing(self) -> None:
        result = list(sample_entries([], SampleOptions(reservoir_size=5)))
        assert result == []
