"""Extractor data models."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TextSource(str, Enum):
    """Source of extracted text."""

    SUBTITLE = "subtitle"
    ASR = "asr"
    OCR = "ocr"


@dataclass
class TextSegment:
    """A segment of extracted text with timestamps."""

    source: TextSource
    start_time: float
    end_time: float
    text: str
    confidence: float = 1.0
    extra: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "source": self.source.value,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "text": self.text,
            "confidence": self.confidence,
        }


@dataclass
class MergedResult:
    """Result of merging multiple sources."""

    segments: list[TextSegment]
    full_text: str
    stats: dict
