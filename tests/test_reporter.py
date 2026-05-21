"""Tests for logslice.reporter."""

from datetime import datetime, timezone
import io

from logslice.aggregator import Bucket
from logslice.reporter import _bar, format_report, write_report


def _bucket(
    second: int = 0,
    count: int = 5,
    by_severity: dict | None = None,
) -> Bucket:
    start = datetime(2024, 1, 1, 0, 0, second, tzinfo=timezone.utc)
    b = Bucket(start=start, count=count, by_severity=by_severity or {})
    return b


# ---------------------------------------------------------------------------
# _bar
# ---------------------------------------------------------------------------

def test_bar_full_when_count_equals_max():
    assert _bar(10, 10, width=10) == "#" * 10


def test_bar_empty_when_zero_max():
    assert _bar(0, 0) == ""


def test_bar_half_filled():
    result = _bar(5, 10, width=10)
    assert result.count("#") == 5
    assert result.count("-") == 5


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------

def test_no_buckets_returns_no_data_message():
    lines = format_report([])
    assert lines == ["No data to report."]


def test_report_contains_timestamp():
    lines = format_report([_bucket(0)])
    assert any("2024-01-01" in line for line in lines)


def test_report_contains_entry_count():
    lines = format_report([_bucket(0, count=7)])
    assert any("7 entries" in line for line in lines)


def test_report_contains_severity_breakdown():
    b = _bucket(0, count=3, by_severity={"INFO": 2, "ERROR": 1})
    lines = format_report([b], severity_breakdown=True)
    assert any("INFO" in line for line in lines)
    assert any("ERROR" in line for line in lines)


def test_no_severity_when_disabled():
    b = _bucket(0, count=3, by_severity={"INFO": 3})
    lines = format_report([b], severity_breakdown=False)
    assert not any("INFO" in line for line in lines)


def test_bar_absent_when_show_bar_false():
    lines = format_report([_bucket(0)], show_bar=False)
    assert not any("[" in line for line in lines)


def test_multiple_buckets_produce_multiple_header_lines():
    buckets = [_bucket(0, 4), _bucket(60, 2)]
    lines = format_report(buckets)
    entry_lines = [l for l in lines if "entries" in l]
    assert len(entry_lines) == 2


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------

def test_write_report_returns_line_count():
    buf = io.StringIO()
    n = write_report([_bucket(0)], dest=buf)
    assert n > 0


def test_write_report_writes_to_dest():
    buf = io.StringIO()
    write_report([_bucket(0, count=3)], dest=buf)
    assert "3 entries" in buf.getvalue()


def test_write_report_empty_buckets():
    buf = io.StringIO()
    n = write_report([], dest=buf)
    assert n == 1
    assert "No data" in buf.getvalue()
