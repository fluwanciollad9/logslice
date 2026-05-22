"""High-level pipeline that wires all logslice stages together."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.highlighter import HighlightOptions, highlight_entries
from logslice.truncator import TruncateOptions, truncate_entries
from logslice.deduplicator import DedupeOptions, deduplicate_entries
from logslice.sampler import SampleOptions, sample_entries
from logslice.contextualizer import ContextOptions, contextualize_entries
from logslice.tagger import TaggerOptions, tag_entries


@dataclass
class PipelineOptions:
    filter: FilterOptions | None = None
    highlight: HighlightOptions | None = None
    truncate: TruncateOptions | None = None
    dedupe: DedupeOptions | None = None
    sample: SampleOptions | None = None
    context: ContextOptions | None = None
    tagger: TaggerOptions | None = None


def run_pipeline(
    entries: Iterable[LogEntry],
    options: PipelineOptions | None = None,
) -> Iterator[LogEntry]:
    """Apply all enabled pipeline stages in order and yield resulting entries."""
    if options is None:
        options = PipelineOptions()

    stream: Iterable[LogEntry] = entries

    if options.tagger is not None:
        stream = tag_entries(stream, options.tagger)

    if options.filter is not None:
        stream = filter_entries(stream, options.filter)

    if options.dedupe is not None:
        stream = deduplicate_entries(stream, options.dedupe)

    if options.sample is not None:
        stream = sample_entries(stream, options.sample)

    if options.context is not None:
        stream = contextualize_entries(stream, options.context)

    if options.truncate is not None:
        stream = truncate_entries(stream, options.truncate)

    if options.highlight is not None:
        stream = highlight_entries(stream, options.highlight)

    yield from stream
