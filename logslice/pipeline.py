"""End-to-end pipeline: slice → filter → transform → annotate → batch → write."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Iterable, Iterator, List, Optional

from logslice.annotator import AnnotateOptions, annotate_entries
from logslice.batcher import BatchOptions, batch_entries
from logslice.filter import FilterOptions, filter_entries
from logslice.formatter import FormatOptions, format_entries
from logslice.highlighter import HighlightOptions, highlight_entries
from logslice.masker import MaskOptions, mask_entries
from logslice.parser import LogEntry
from logslice.ratelimiter import RateLimitOptions, ratelimit_entries
from logslice.sampler import SampleOptions, sample_entries
from logslice.scoper import ScopeOptions, scope_entries
from logslice.sorter import SortOptions, sort_entries
from logslice.tagger import TaggerOptions, tag_entries
from logslice.throttler import ThrottleOptions, throttle_entries
from logslice.transformer import TransformOptions, transform_entries
from logslice.truncator import TruncateOptions, truncate_entries
from logslice.writer import write_entries


@dataclass
class PipelineOptions:
    filter: FilterOptions = field(default_factory=FilterOptions)
    sample: Optional[SampleOptions] = None
    mask: Optional[MaskOptions] = None
    tagger: Optional[TaggerOptions] = None
    ratelimit: Optional[RateLimitOptions] = None
    throttle: Optional[ThrottleOptions] = None
    transform: Optional[TransformOptions] = None
    truncate: Optional[TruncateOptions] = None
    annotate: Optional[AnnotateOptions] = None
    highlight: Optional[HighlightOptions] = None
    sort: Optional[SortOptions] = None
    scope: Optional[ScopeOptions] = None
    batch: Optional[BatchOptions] = None
    format: FormatOptions = field(default_factory=FormatOptions)


def run_pipeline(
    entries: Iterable[LogEntry],
    options: PipelineOptions | None = None,
    output: IO[str] | None = None,
) -> int:
    """Run *entries* through the full pipeline and write formatted output.

    Returns the number of entries written.
    """
    if options is None:
        options = PipelineOptions()

    stream: Iterator[LogEntry] = iter(entries)

    if options.mask:
        stream = mask_entries(stream, options.mask)
    if options.tagger:
        stream = tag_entries(stream, options.tagger)
    stream = filter_entries(stream, options.filter)
    if options.ratelimit:
        stream = ratelimit_entries(stream, options.ratelimit)
    if options.throttle:
        stream = throttle_entries(stream, options.throttle)
    if options.sample:
        stream = sample_entries(stream, options.sample)
    if options.transform:
        stream = transform_entries(stream, options.transform)
    if options.truncate:
        stream = truncate_entries(stream, options.truncate)
    if options.annotate:
        stream = annotate_entries(stream, options.annotate)
    if options.sort:
        stream = sort_entries(stream, options.sort)
    if options.scope:
        stream = scope_entries(stream, options.scope)

    # If batching is requested, flatten batches back to entries for writing.
    if options.batch:
        def _flatten_batches(s: Iterator[LogEntry]) -> Iterator[LogEntry]:
            for batch in batch_entries(s, options.batch):
                yield from batch.entries
        stream = _flatten_batches(stream)

    if options.highlight:
        stream = highlight_entries(stream, options.highlight)

    formatted = format_entries(stream, options.format)
    kwargs = {} if output is None else {"output": output}
    return write_entries(formatted, **kwargs)
