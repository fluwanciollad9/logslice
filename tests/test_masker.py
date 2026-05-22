"""Tests for logslice.masker."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from logslice.masker import MaskOptions, mask_entries, mask_entry
from logslice.parser import LogEntry


def _entry(message: str) -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        severity="INFO",
        message=message,
        raw=message,
        tags={},
    )


# ---------------------------------------------------------------------------
# MaskOptions validation
# ---------------------------------------------------------------------------

class TestMaskOptions:
    def test_defaults_are_empty(self):
        opts = MaskOptions()
        assert opts.builtins == []
        assert opts.custom_patterns == []
        assert opts.replacement == "[REDACTED]"

    def test_unknown_builtin_raises(self):
        with pytest.raises(ValueError, match="Unknown builtin"):
            MaskOptions(builtins=["credit_card"])

    def test_invalid_custom_pattern_raises(self):
        with pytest.raises(ValueError, match="Invalid custom pattern"):
            MaskOptions(custom_patterns=["(unclosed"])

    def test_valid_builtins_accepted(self):
        opts = MaskOptions(builtins=["ipv4", "email"])
        assert opts.builtins == ["ipv4", "email"]


# ---------------------------------------------------------------------------
# mask_entry
# ---------------------------------------------------------------------------

class TestMaskEntry:
    def test_ipv4_redacted(self):
        opts = MaskOptions(builtins=["ipv4"])
        result = mask_entry(_entry("connected from 192.168.1.1 ok"), opts)
        assert "192.168.1.1" not in result.message
        assert "[REDACTED]" in result.message

    def test_email_redacted(self):
        opts = MaskOptions(builtins=["email"])
        result = mask_entry(_entry("user alice@example.com logged in"), opts)
        assert "alice@example.com" not in result.message
        assert "[REDACTED]" in result.message

    def test_uuid_redacted(self):
        opts = MaskOptions(builtins=["uuid"])
        msg = "request id=550e8400-e29b-41d4-a716-446655440000 done"
        result = mask_entry(_entry(msg), opts)
        assert "550e8400" not in result.message

    def test_jwt_redacted(self):
        opts = MaskOptions(builtins=["jwt"])
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = mask_entry(_entry(f"token={token}"), opts)
        assert token not in result.message

    def test_custom_pattern_redacted(self):
        opts = MaskOptions(custom_patterns=[r"secret-\w+"])
        result = mask_entry(_entry("key=secret-abc123 used"), opts)
        assert "secret-abc123" not in result.message
        assert "[REDACTED]" in result.message

    def test_no_patterns_returns_original_message(self):
        opts = MaskOptions()
        entry = _entry("hello 192.168.0.1")
        result = mask_entry(entry, opts)
        assert result.message == entry.message

    def test_custom_replacement_string(self):
        opts = MaskOptions(builtins=["ipv4"], replacement="***")
        result = mask_entry(_entry("ip=10.0.0.1"), opts)
        assert "***" in result.message

    def test_original_entry_unchanged(self):
        opts = MaskOptions(builtins=["ipv4"])
        original = _entry("ip=10.0.0.1")
        mask_entry(original, opts)
        assert original.message == "ip=10.0.0.1"


# ---------------------------------------------------------------------------
# mask_entries
# ---------------------------------------------------------------------------

def test_none_opts_yields_unchanged():
    entries = [_entry("ip=1.2.3.4"), _entry("email=a@b.com")]
    result = list(mask_entries(entries, opts=None))
    assert [e.message for e in result] == [e.message for e in entries]


def test_mask_entries_applies_to_all():
    opts = MaskOptions(builtins=["ipv4"])
    entries = [_entry("a 1.2.3.4"), _entry("b 5.6.7.8"), _entry("no ip here")]
    result = list(mask_entries(entries, opts))
    assert "1.2.3.4" not in result[0].message
    assert "5.6.7.8" not in result[1].message
    assert result[2].message == "no ip here"


def test_mask_entries_is_lazy():
    opts = MaskOptions(builtins=["email"])
    gen = mask_entries(iter([_entry("x@y.com")]), opts)
    assert hasattr(gen, "__next__")
