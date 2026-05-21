"""End-to-end pipeline wiring for logslice."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.sampler import SampleOptions, sample_entries
from logslice.deduplicator import DedupeOptions, deduplicate_entries
from logslice.highlighter import HighlightOptions, highlight_entries
from logslice.truncator import TruncateOptions, truncate_entries


@dataclass
class PipelineOptions:
    """Aggregated options for the full processing pipeline."""

    filter: FilterOptions = field(default_factory=FilterOptions)
    sample: SampleOptions = field(default_factory=SampleOptions)
    dedupe: DedupeOptions = field(default_factory=DedupeOptions)
    highlight: HighlightOptions = field(default_factory=HighlightOptions)
    truncate: TruncateOptions = field(default_factory=TruncateOptions)
    enable_truncate: bool = False
    enable_dedupe: bool = False
    enable_highlight: bool = False


def run_pipeline(
    entries: Iterable[LogEntry],
    opts: PipelineOptions | None = None,
) -> Iterator[LogEntry]:
    """Pass *entries* through the configured pipeline stages."""
    if opts is None:
        opts = PipelineOptions()

    stream: Iterable[LogEntry] = entries
    stream = filter_entries(stream, opts.filter)
    stream = sample_entries(stream, opts.sample)

    if opts.enable_dedupe:
        stream = deduplicate_entries(stream, opts.dedupe)

    if opts.enable_truncate:
        stream = truncate_entries(stream, opts.truncate)

    if opts.enable_highlight:
        stream = highlight_entries(stream, opts.highlight)

    yield from stream
