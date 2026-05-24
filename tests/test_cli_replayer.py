"""Tests for logslice.cli_replayer."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from logslice.cli_replayer import add_replay_subparser, _run_replay


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command")
    add_replay_subparser(sub)
    return p


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        file="-",
        speed=1.0,
        max_delay=5.0,
        dry_run=False,
        func=_run_replay,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestAddReplaySubparser:
    def test_subparser_registered(self):
        p = _parser()
        args = p.parse_args(["replay", "-"])
        assert args.command == "replay"

    def test_default_speed(self):
        p = _parser()
        args = p.parse_args(["replay"])
        assert args.speed == 1.0

    def test_default_max_delay(self):
        p = _parser()
        args = p.parse_args(["replay"])
        assert args.max_delay == 5.0

    def test_dry_run_flag_false_by_default(self):
        p = _parser()
        args = p.parse_args(["replay"])
        assert args.dry_run is False

    def test_dry_run_flag_enabled(self):
        p = _parser()
        args = p.parse_args(["replay", "--dry-run"])
        assert args.dry_run is True

    def test_speed_parsed(self):
        p = _parser()
        args = p.parse_args(["replay", "--speed", "2.5"])
        assert args.speed == 2.5

    def test_max_delay_parsed(self):
        p = _parser()
        args = p.parse_args(["replay", "--max-delay", "10"])
        assert args.max_delay == 10.0


class TestRunReplay:
    def test_invalid_speed_returns_error_code(self):
        args = _make_args(speed=-1.0)
        rc = _run_replay(args)
        assert rc == 1

    def test_invalid_max_delay_returns_error_code(self):
        args = _make_args(max_delay=-5.0)
        rc = _run_replay(args)
        assert rc == 1
