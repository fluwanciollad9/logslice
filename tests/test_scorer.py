"""Tests for logslice.scorer."""
from __future__ import annotations

from datetime import datetime

import pytest

from logslice.parser import LogEntry
from logslice.scorer import ScoreOptions, _score_entry, score_entries


def _entry(severity: str = "INFO", message: str = "hello world") -> LogEntry:
    return LogEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        severity=severity,
        message=message,
        raw=f"{severity} {message}",
    )


class TestScoreOptions:
    def test_defaults(self) -> None:
        opts = ScoreOptions()
        assert opts.keywords == []
        assert opts.threshold == 0.0

    def test_negative_keyword_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="keyword_weight"):
            ScoreOptions(keyword_weight=-1.0)

    def test_negative_severity_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="severity_weight"):
            ScoreOptions(severity_weight=-0.5)

    def test_threshold_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold"):
            ScoreOptions(threshold=1.1)

    def test_threshold_below_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold"):
            ScoreOptions(threshold=-0.1)


class TestScoreEntry:
    def test_critical_scores_higher_than_debug(self) -> None:
        opts = ScoreOptions(keyword_weight=0.0)
        s_crit = _score_entry(_entry("CRITICAL"), opts)
        s_debug = _score_entry(_entry("DEBUG"), opts)
        assert s_crit > s_debug

    def test_keyword_hit_increases_score(self) -> None:
        opts = ScoreOptions(keywords=["error"], severity_weight=0.0)
        s_hit = _score_entry(_entry(message="an error occurred"), opts)
        s_miss = _score_entry(_entry(message="all good"), opts)
        assert s_hit > s_miss

    def test_score_clamped_to_one(self) -> None:
        opts = ScoreOptions(keywords=["x"], keyword_weight=100.0, severity_weight=100.0)
        score = _score_entry(_entry("CRITICAL", "x"), opts)
        assert score <= 1.0

    def test_score_clamped_to_zero(self) -> None:
        opts = ScoreOptions(keywords=["missing"], severity_weight=0.0)
        score = _score_entry(_entry("DEBUG", "nothing here"), opts)
        assert score >= 0.0

    def test_unknown_severity_treated_as_zero(self) -> None:
        opts = ScoreOptions(keyword_weight=0.0)
        score = _score_entry(_entry("TRACE"), opts)
        assert score == 0.0

    def test_zero_total_weight_returns_zero(self) -> None:
        opts = ScoreOptions(keyword_weight=0.0, severity_weight=0.0)
        score = _score_entry(_entry("CRITICAL", "error"), opts)
        assert score == 0.0


class TestScoreEntries:
    def test_all_entries_returned_with_default_threshold(self) -> None:
        entries = [_entry("DEBUG"), _entry("INFO"), _entry("ERROR")]
        results = list(score_entries(entries))
        assert len(results) == 3

    def test_threshold_filters_low_scores(self) -> None:
        entries = [_entry("DEBUG"), _entry("CRITICAL")]
        opts = ScoreOptions(threshold=0.5, keyword_weight=0.0)
        results = list(score_entries(entries, opts))
        assert len(results) == 1
        assert results[0][0].severity == "CRITICAL"

    def test_yields_entry_score_pairs(self) -> None:
        entries = [_entry("ERROR")]
        results = list(score_entries(entries))
        entry, score = results[0]
        assert isinstance(score, float)
        assert entry.severity == "ERROR"

    def test_empty_input_yields_nothing(self) -> None:
        assert list(score_entries([])) == []
