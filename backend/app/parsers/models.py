"""Parser data models."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlatformType(str, Enum):
    """Supported platforms."""

    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    KUAISHOU = "kuaishou"
    XIAOHONGSHU = "xiaohongshu"
    WEIXIN = "weixin"
    LOCAL = "local"
    UNKNOWN = "unknown"


@dataclass
class MediaResource:
    """Single media resource (video or image)."""

    url: Optional[str] = None
    local_path: Optional[str] = None
    media_type: str = "video"
    duration_sec: Optional[float] = None
    subtitle_url: Optional[str] = None


@dataclass
class PlatformParseResult:
    """Result of platform parsing."""

    platform: PlatformType
    media_list: list[MediaResource]
    metadata: dict
    raw_input: str
    error: Optional[str] = None


class UnsupportedPlatformError(Exception):
    """Unsupported platform or input."""

    def __init__(self, message: str, platform: Optional[PlatformType] = None):
        self.message = message
        self.platform = platform
        super().__init__(message)
