"""Integration tests: masker wired into the pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from logslice.masker import MaskOptions, mask_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.parser import LogEntry


def _entry(message: str, severity: str = "INFO") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 6, 1, 8, 0, 0, tzinfo=timezone.utc),
        severity=severity,
        message=message,
        raw=message,
        tags={},
    )


def _run(
    entries: List[LogEntry],
    mask_opts: MaskOptions | None = None,
    filter_opts: FilterOptions | None = None,
) -> List[LogEntry]:
    stream = iter(entries)
    if mask_opts is not None:
        stream = mask_entries(stream, mask_opts)
    if filter_opts is not None:
        stream = filter_entries(stream, filter_opts)
    return list(stream)


class TestPipelineMasker:
    def test_masking_disabled_by_default(self):
        entries = [_entry("ip=192.168.0.1")]
        result = _run(entries)
        assert result[0].message == "ip=192.168.0.1"

    def test_masking_applied_before_filter(self):
        """After masking, the original IP should not appear in any output."""
        opts = MaskOptions(builtins=["ipv4"])
        entries = [
            _entry("connection from 10.0.0.1"),
            _entry("no sensitive data here"),
        ]
        result = _run(entries, mask_opts=opts)
        assert all("10.0.0.1" not in e.message for e in result)

    def test_filter_sees_masked_message(self):
        """Filter keyword matching operates on the already-masked message."""
        mask_opts = MaskOptions(builtins=["email"])
        filter_opts = FilterOptions(include_keywords=["[REDACTED]"])
        entries = [
            _entry("user admin@corp.com signed in"),
            _entry("server restarted"),
        ]
        result = _run(entries, mask_opts=mask_opts, filter_opts=filter_opts)
        assert len(result) == 1
        assert "[REDACTED]" in result[0].message

    def test_multiple_builtins_all_redacted(self):
        mask_opts = MaskOptions(builtins=["ipv4", "email"])
        entries = [_entry("from 10.1.2.3 user foo@bar.com")]
        result = _run(entries, mask_opts=mask_opts)
        msg = result[0].message
        assert "10.1.2.3" not in msg
        assert "foo@bar.com" not in msg
        assert msg.count("[REDACTED]") == 2
