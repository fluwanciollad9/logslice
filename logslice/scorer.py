"""Entry relevance scorer that assigns a numeric score to log entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry

_SEVERITY_WEIGHTS: dict[str, float] = {
    "DEBUG": 0.1,
    "INFO": 0.3,
    "WARNING": 0.6,
    "ERROR": 0.9,
    "CRITICAL": 1.0,
}


@dataclass
class ScoreOptions:
    keywords: list[str] = field(default_factory=list)
    keyword_weight: float = 1.0
    severity_weight: float = 1.0
    threshold: float = 0.0

    def __post_init__(self) -> None:
        if self.keyword_weight < 0:
            raise ValueError("keyword_weight must be >= 0")
        if self.severity_weight < 0:
            raise ValueError("severity_weight must be >= 0")
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError("threshold must be between 0.0 and 1.0")


def _score_entry(entry: LogEntry, opts: ScoreOptions) -> float:
    """Return a relevance score in [0.0, 1.0] for *entry*."""
    severity = (entry.severity or "").upper()
    sev_score = _SEVERITY_WEIGHTS.get(severity, 0.0) * opts.severity_weight

    kw_score = 0.0
    if opts.keywords:
        message = entry.message or ""
        hits = sum(1 for kw in opts.keywords if kw.lower() in message.lower())
        kw_score = (hits / len(opts.keywords)) * opts.keyword_weight

    total_weight = opts.severity_weight + opts.keyword_weight
    if total_weight == 0:
        return 0.0
    raw = (sev_score + kw_score) / total_weight
    return min(1.0, max(0.0, raw))


def score_entries(
    entries: Iterable[LogEntry],
    opts: ScoreOptions | None = None,
) -> Iterator[tuple[LogEntry, float]]:
    """Yield *(entry, score)* pairs, filtering out entries below *threshold*."""
    if opts is None:
        opts = ScoreOptions()
    for entry in entries:
        score = _score_entry(entry, opts)
        if score >= opts.threshold:
            yield entry, score
