"""Local file parser adapter."""
import os
from pathlib import Path

from app.parsers.base import IPlatformParser
from app.parsers.models import MediaResource, PlatformParseResult, PlatformType


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def is_local_file(input_str: str) -> bool:
    """Check if input is a local file path."""
    s = input_str.strip()
    if s.startswith("file://"):
        return True
    path = Path(s)
    return path.exists() and path.is_file()


def resolve_path(input_str: str) -> Path:
    """Resolve input to filesystem path."""
    s = input_str.strip()
    if s.startswith("file://"):
        s = s[7:]
    return Path(s).resolve()


class LocalAdapter(IPlatformParser):
    """Parse local video/image files."""

    @property
    def platform(self) -> PlatformType:
        return PlatformType.LOCAL

    def can_handle(self, input_str: str) -> bool:
        return is_local_file(input_str)

    def parse(self, input_str: str) -> PlatformParseResult:
        path = resolve_path(input_str)
        if not path.exists():
            return PlatformParseResult(
                platform=PlatformType.LOCAL,
                media_list=[],
                metadata={},
                raw_input=input_str,
                error="文件不存在",
            )

        ext = path.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            media_type = "video"
        elif ext in IMAGE_EXTENSIONS:
            media_type = "image"
        else:
            return PlatformParseResult(
                platform=PlatformType.LOCAL,
                media_list=[],
                metadata={},
                raw_input=input_str,
                error=f"不支持的格式: {ext}",
            )

        return PlatformParseResult(
            platform=PlatformType.LOCAL,
            media_list=[
                MediaResource(
                    local_path=str(path),
                    media_type=media_type,
                )
            ],
            metadata={"filename": path.name},
            raw_input=input_str,
        )
