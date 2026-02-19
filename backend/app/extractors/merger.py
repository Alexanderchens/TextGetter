"""Merge and deduplicate text segments from multiple sources."""
from app.extractors.models import MergedResult, TextSegment, TextSource

# Priority: higher = prefer when overlapping
SOURCE_PRIORITY = {
    TextSource.SUBTITLE: 3,
    TextSource.ASR: 2,
    TextSource.OCR: 1,
}


def _similarity(a: str, b: str) -> float:
    """Simple Jaccard-like similarity for Chinese/English."""
    a_set = set(a) if len(a) < 50 else set(a[i:i+2] for i in range(len(a)-1))
    b_set = set(b) if len(b) < 50 else set(b[i:i+2] for i in range(len(b)-1))
    if not a_set or not b_set:
        return 0.0
    return len(a_set & b_set) / len(a_set | b_set)


def _is_duplicate(seg_a: TextSegment, seg_b: TextSegment, threshold: float = 0.85) -> bool:
    """Check if two segments are duplicates (overlapping time + similar text)."""
    time_gap = abs(seg_a.start_time - seg_b.start_time)
    if time_gap > 1.0:
        return False
    return _similarity(seg_a.text, seg_b.text) > threshold


def merge(segments: list[TextSegment]) -> MergedResult:
    """Merge segments from multiple sources, deduplicate, sort by time."""
    if not segments:
        return MergedResult(segments=[], full_text="", stats={})

    # Sort by start_time, then by source priority
    sorted_segs = sorted(
        segments,
        key=lambda s: (s.start_time, -SOURCE_PRIORITY.get(s.source, 0)),
    )

    merged: list[TextSegment] = []
    for seg in sorted_segs:
        skip = False
        for existing in merged:
            if _is_duplicate(seg, existing):
                # Prefer higher priority source
                if SOURCE_PRIORITY.get(seg.source, 0) <= SOURCE_PRIORITY.get(existing.source, 0):
                    skip = True
                    break
        if not skip:
            merged.append(seg)

    # Sort by start_time for final output
    merged.sort(key=lambda s: s.start_time)

    # Build full text
    full_text = "\n\n".join(s.text for s in merged)

    # Stats
    stats = {}
    for src in TextSource:
        count = sum(1 for s in merged if s.source == src)
        chars = sum(len(s.text) for s in merged if s.source == src)
        if count > 0:
            stats[src.value] = {"segmentCount": count, "charCount": chars}

    return MergedResult(segments=merged, full_text=full_text, stats=stats)
