"""ASR extractor using Whisper."""
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from app.extractors.models import TextSegment, TextSource


def _extract_audio(video_path: str, output_path: str) -> str:
    """Extract audio from video using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def _whisper_to_segments(result: dict) -> list[TextSegment]:
    """Convert Whisper result to TextSegments."""
    segments = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if not text:
            continue
        segments.append(TextSegment(
            source=TextSource.ASR,
            start_time=float(seg.get("start", 0)),
            end_time=float(seg.get("end", 0)),
            text=text,
            confidence=1.0,
        ))
    return segments


class ASRExtractor:
    """Extract speech from video using Whisper."""

    def __init__(self, model_size: str = "base", language: str = "zh"):
        self.model_size = model_size
        self.language = language
        self._model = None

    def _load_model(self):
        """Lazy load Whisper model."""
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_size)
        return self._model

    def extract(
        self,
        media_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[TextSegment]:
        """Extract speech from video."""
        try:
            model = self._load_model()
        except Exception as e:
            return []  # Fallback: no ASR if whisper not available

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name
        try:
            _extract_audio(media_path, audio_path)
            result = model.transcribe(
                audio_path,
                language=self.language,
                word_timestamps=False,
            )
            return _whisper_to_segments(result)
        finally:
            Path(audio_path).unlink(missing_ok=True)
