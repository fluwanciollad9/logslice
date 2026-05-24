"""Pipeline: orchestrate all processing stages over a stream of LogEntry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional

from logslice.parser import LogEntry
from logslice.filter import FilterOptions, filter_entries
from logslice.sampler import SampleOptions, sample_entries
from logslice.deduplicator import DedupeOptions, deduplicate_entries
from logslice.highlighter import HighlightOptions, highlight_entries
from logslice.truncator import TruncateOptions, truncate_entries
from logslice.tagger import TaggerOptions, tag_entries
from logslice.ratelimiter import RateLimitOptions, ratelimit_entries
from logslice.masker import MaskOptions, mask_entries
from logslice.sorter import SortOptions, sort_entries
from logslice.annotator import AnnotateOptions, annotate_entries
from logslice.diffier import DiffOptions, diff_entries
from logslice.throttler import ThrottleOptions, throttle_entries
from logslice.scoper import ScopeOptions, scope_entries
from logslice.flattener import FlattenOptions, flatten_entries
from logslice.joiner import JoinOptions, join_entries
from logslice.capper import CapOptions, cap_entries
from logslice.replayer import ReplayOptions, replay_entries
from logslice.labeler import LabelOptions, label_entries


@dataclass
class PipelineOptions:
    filter: FilterOptions = field(default_factory=FilterOptions)
    sample: Optional[SampleOptions] = None
    dedupe: Optional[DedupeOptions] = None
    highlight: Optional[HighlightOptions] = None
    truncate: Optional[TruncateOptions] = None
    tagger: Optional[TaggerOptions] = None
    ratelimit: Optional[RateLimitOptions] = None
    mask: Optional[MaskOptions] = None
    sort: Optional[SortOptions] = None
    annotate: Optional[AnnotateOptions] = None
    diff: Optional[DiffOptions] = None
    throttle: Optional[ThrottleOptions] = None
    scope: Optional[ScopeOptions] = None
    flatten: Optional[FlattenOptions] = None
    join: Optional[JoinOptions] = None
    cap: Optional[CapOptions] = None
    replay: Optional[ReplayOptions] = None
    label: Optional[LabelOptions] = None


def run_pipeline(
    entries: Iterable[LogEntry], opts: PipelineOptions
) -> Iterator[LogEntry]:
    """Run *entries* through every enabled pipeline stage in order."""
    stream: Iterable[LogEntry] = entries

    if opts.flatten is not None:
        stream = flatten_entries(stream, opts.flatten)

    if opts.join is not None:
        stream = join_entries(stream, opts.join)

    if opts.mask is not None:
        stream = mask_entries(stream, opts.mask)

    if opts.tagger is not None:
        stream = tag_entries(stream, opts.tagger)

    if opts.label is not None:
        stream = _apply_label_after_filter(stream, opts)
        return stream

    stream = filter_entries(stream, opts.filter)

    if opts.label is not None:
        stream = label_entries(stream, opts.label)

    stream = _apply_post_filter(stream, opts)
    return stream


def _apply_label_after_filter(
    stream: Iterable[LogEntry], opts: PipelineOptions
) -> Iterator[LogEntry]:
    """Filter first, then label, then apply remaining stages."""
    filtered = filter_entries(stream, opts.filter)
    labeled = label_entries(filtered, opts.label)  # type: ignore[arg-type]
    return _apply_post_filter(labeled, opts)


def _apply_post_filter(
    stream: Iterable[LogEntry], opts: PipelineOptions
) -> Iterator[LogEntry]:
    if opts.ratelimit is not None:
        stream = ratelimit_entries(stream, opts.ratelimit)
    if opts.dedupe is not None:
        stream = deduplicate_entries(stream, opts.dedupe)
    if opts.sample is not None:
        stream = sample_entries(stream, opts.sample)
    if opts.throttle is not None:
        stream = throttle_entries(stream, opts.throttle)
    if opts.cap is not None:
        stream = cap_entries(stream, opts.cap)
    if opts.scope is not None:
        stream = scope_entries(stream, opts.scope)
    if opts.truncate is not None:
        stream = truncate_entries(stream, opts.truncate)
    if opts.diff is not None:
        stream = diff_entries(stream, opts.diff)
    if opts.annotate is not None:
        stream = annotate_entries(stream, opts.annotate)
    if opts.highlight is not None:
        stream = highlight_entries(stream, opts.highlight)
    if opts.sort is not None:
        stream = _flatten_batches(sort_entries(stream, opts.sort))
    if opts.replay is not None:
        stream = replay_entries(stream, opts.replay)
    return stream  # type: ignore[return-value]


def _flatten_batches(batches: Iterable[List[LogEntry]]) -> Iterator[LogEntry]:
    for batch in batches:
        yield from batch
