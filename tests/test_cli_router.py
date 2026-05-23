"""Tests for logslice.cli_router."""
from __future__ import annotations

import argparse
import pytest

from logslice.cli_router import add_route_subparser, _parse_rules
from logslice.router import RouteRule


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "rules": [],
        "default_channel": "default",
        "drop_unmatched": False,
        "file": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestAddRouteSubparser:
    def _parser(self):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers()
        add_route_subparser(sub)
        return p

    def test_subparser_registered(self):
        p = self._parser()
        ns = p.parse_args(["route"])
        assert hasattr(ns, "func")

    def test_default_channel_default(self):
        p = self._parser()
        ns = p.parse_args(["route"])
        assert ns.default_channel == "default"

    def test_drop_unmatched_default_false(self):
        p = self._parser()
        ns = p.parse_args(["route"])
        assert ns.drop_unmatched is False

    def test_rule_flag_accumulates(self):
        p = self._parser()
        ns = p.parse_args(["route", "--rule", "errors:s:ERROR", "--rule", "db:k:database"])
        assert len(ns.rules) == 2

    def test_custom_default_channel(self):
        p = self._parser()
        ns = p.parse_args(["route", "--default-channel", "misc"])
        assert ns.default_channel == "misc"


class TestParseRules:
    def test_severity_prefix(self):
        rules = _parse_rules(["errors:s:ERROR"])
        assert len(rules) == 1
        assert rules[0].channel == "errors"
        assert rules[0].severity == "ERROR"
        assert rules[0].keyword is None

    def test_keyword_prefix(self):
        rules = _parse_rules(["db:k:database"])
        assert rules[0].channel == "db"
        assert rules[0].keyword == "database"
        assert rules[0].severity is None

    def test_bare_value_treated_as_keyword(self):
        rules = _parse_rules(["ch:timeout"])
        assert rules[0].keyword == "timeout"

    def test_empty_list_returns_empty(self):
        assert _parse_rules([]) == []

    def test_multiple_rules_parsed(self):
        rules = _parse_rules(["a:s:ERROR", "b:k:crash"])
        assert len(rules) == 2

    def test_missing_colon_raises(self):
        with pytest.raises((argparse.ArgumentTypeError, ValueError)):
            _parse_rules(["badformat"])
