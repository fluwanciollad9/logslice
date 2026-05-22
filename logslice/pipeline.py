"""Pipeline orchestration for logslice."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.sampler import SampleOptions, sample_entries
from logslice.deduplicator import DedupeOptions, deduplicate_entries
from logslice.highlighter import HighlightOptions, highlight_entries
from logslice.truncator import TruncateOptions, truncate_entries
from logslice.tagger import TaggerOptions, tag_entries
from logslice.ratelimiter import RateLimitOptions, ratelimit_entries
from logslice.masker import MaskOptions, mask_entries
from logslice.splitter import SplitOptions, split_entries
from logslice.sorter import SortOptions, sort_entries


@dataclass
class PipelineOptions:
    filter: Optional[FilterOptions] = None
    sample: Optional[SampleOptions] = None
    dedupe: Optional[DedupeOptions] = None
    highlight: Optional[HighlightOptions] = None
    truncate: Optional[TruncateOptions] = None
    tagger: Optional[TaggerOptions] = None
    ratelimit: Optional[RateLimitOptions] = None
    mask: Optional[MaskOptions] = None
    split: Optional[SplitOptions] = None
    sort: Optional[SortOptions] = None


def run_pipeline(
    entries: Iterable[LogEntry],
    opts: PipelineOptions | None = None,
) -> Iterator[LogEntry]:
    """Run *entries* through the configured pipeline stages and yield results."""
    if opts is None:
        opts = PipelineOptions()

    stream: Iterable[LogEntry] = entries

    if opts.mask is not None:
        stream = mask_entries(stream, opts.mask)

    if opts.tagger is not None:
        stream = tag_entries(stream, opts.tagger)

    if opts.filter is not None:
        stream = filter_entries(stream, opts.filter)

    if opts.ratelimit is not None:
        stream = ratelimit_entries(stream, opts.ratelimit)

    if opts.dedupe is not None:
        stream = deduplicate_entries(stream, opts.dedupe)

    if opts.sample is not None:
        stream = sample_entries(stream, opts.sample)

    if opts.truncate is not None:
        stream = truncate_entries(stream, opts.truncate)

    if opts.highlight is not None:
        stream = highlight_entries(stream, opts.highlight)

    if opts.split is not None:
        stream = split_entries(stream, opts.split)

    if opts.sort is not None:
        stream = sort_entries(stream, opts.sort)

    yield from stream
