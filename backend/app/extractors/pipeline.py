"""Extraction pipeline orchestrator."""
from pathlib import Path
from typing import Callable, Optional

from app.config import get_settings
from app.extractors.asr import ASRExtractor
from app.extractors.merger import merge
from app.extractors.models import MergedResult, TextSegment
from app.extractors.subtitle import SubtitleExtractor


def _progress(stage: str, pct: int, callback: Optional[Callable[[str, int], None]] = None):
    if callback:
        callback(stage, pct)


class ExtractPipeline:
    """Orchestrate subtitle -> ASR -> merge extraction."""

    def __init__(self):
        settings = get_settings()
        self.subtitle_extractor = SubtitleExtractor()
        self.asr_extractor = ASRExtractor(model_size=settings.asr_model)
        self.ocr_interval = settings.ocr_interval

    def run(
        self,
        media_path: str,
        subtitle_path: Optional[str] = None,
        extract_mode: str = "full",  # subtitle_first | full | asr_only
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> MergedResult:
        """Run extraction pipeline."""
        all_segments: list[TextSegment] = []
        path = Path(media_path)

        if not path.exists():
            return MergedResult(segments=[], full_text="", stats={"error": "文件不存在"})

        # Check if video (skip ASR for images)
        is_video = path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".m4v"}

        # 1. Subtitle
        if extract_mode != "asr_only":
            _progress("subtitle", 0, progress_callback)
            sub_segs = self.subtitle_extractor.extract(media_path, subtitle_path)
            all_segments.extend(sub_segs)
            _progress("subtitle", 100, progress_callback)

        # 2. ASR (only for video, and if full or asr_only)
        if is_video and extract_mode in ("full", "asr_only"):
            _progress("asr", 0, progress_callback)
            asr_segs = self.asr_extractor.extract(media_path, progress_callback)
            all_segments.extend(asr_segs)
            _progress("asr", 100, progress_callback)

        # 3. Merge
        _progress("merge", 0, progress_callback)
        result = merge(all_segments)
        _progress("merge", 100, progress_callback)

        return result
