"""Composable pipeline that chains slicer, filter, deduplicator, sampler, and highlighter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.deduplicator import DedupeOptions, deduplicate_entries
from logslice.sampler import SampleOptions, sample_entries
from logslice.highlighter import HighlightOptions, highlight_entries


@dataclass
class PipelineOptions:
    filter: Optional[FilterOptions] = None
    dedupe: Optional[DedupeOptions] = None
    sample: Optional[SampleOptions] = None
    highlight: Optional[HighlightOptions] = None


def run_pipeline(
    entries: Iterable[LogEntry],
    opts: PipelineOptions,
) -> Iterator[LogEntry]:
    """Pass *entries* through each enabled pipeline stage in order.

    Stages are applied only when the corresponding options object is provided.
    Order: filter -> deduplicate -> sample -> highlight.
    """
    stream: Iterable[LogEntry] = entries

    if opts.filter is not None:
        stream = filter_entries(stream, opts.filter)

    if opts.dedupe is not None:
        stream = deduplicate_entries(stream, opts.dedupe)

    if opts.sample is not None:
        stream = sample_entries(stream, opts.sample)

    if opts.highlight is not None:
        stream = highlight_entries(stream, opts.highlight)

    yield from stream
