"""Reservoir and rate-based sampling for large log slices."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional

from logslice.parser import LogEntry


@dataclass
class SampleOptions:
    """Controls how entries are sampled from a slice."""

    # Keep only every Nth matching entry (1 = keep all).
    rate: int = 1
    # If set, use reservoir sampling to return exactly *size* entries.
    reservoir_size: Optional[int] = None
    # Seed for reproducible sampling.
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.rate < 1:
            raise ValueError("rate must be >= 1")
        if self.reservoir_size is not None and self.reservoir_size < 1:
            raise ValueError("reservoir_size must be >= 1")


def _rate_sample(
    entries: Iterable[LogEntry],
    rate: int,
    rng: random.Random,
) -> Iterator[LogEntry]:
    """Yield every *rate*-th entry chosen at random within each window."""
    bucket: List[LogEntry] = []
    for entry in entries:
        bucket.append(entry)
        if len(bucket) == rate:
            yield rng.choice(bucket)
            bucket.clear()
    # Flush any remainder.
    if bucket:
        yield rng.choice(bucket)


def _reservoir_sample(
    entries: Iterable[LogEntry],
    size: int,
    rng: random.Random,
) -> List[LogEntry]:
    """Return a random sample of *size* entries using reservoir sampling."""
    reservoir: List[LogEntry] = []
    for i, entry in enumerate(entries):
        if i < size:
            reservoir.append(entry)
        else:
            j = rng.randint(0, i)
            if j < size:
                reservoir[j] = entry
    return reservoir


def sample_entries(
    entries: Iterable[LogEntry],
    options: SampleOptions,
) -> Iterator[LogEntry]:
    """Apply sampling strategy defined by *options* to *entries*."""
    rng = random.Random(options.seed)

    if options.reservoir_size is not None:
        sampled = _reservoir_sample(entries, options.reservoir_size, rng)
        yield from sampled
        return

    if options.rate == 1:
        yield from entries
        return

    yield from _rate_sample(entries, options.rate, rng)
