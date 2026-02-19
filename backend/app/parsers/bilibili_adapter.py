"""Bilibili video parser adapter using yt-dlp."""
import re
from typing import Optional

from app.parsers.base import IPlatformParser
from app.parsers.models import MediaResource, PlatformParseResult, PlatformType


BILIBILI_PATTERNS = [
    r"bilibili\.com",
    r"b23\.tv",
    r"bili22\.com",
    r"bili33\.com",
]


def is_bilibili_url(input_str: str) -> bool:
    """Check if input is a Bilibili URL."""
    s = input_str.strip()
    if not s or s.startswith("file://"):
        return False
    return any(re.search(p, s, re.IGNORECASE) for p in BILIBILI_PATTERNS)


class BilibiliAdapter(IPlatformParser):
    """Parse Bilibili video URLs. Uses yt-dlp for extraction."""

    @property
    def platform(self) -> PlatformType:
        return PlatformType.BILIBILI

    def can_handle(self, input_str: str) -> bool:
        return is_bilibili_url(input_str)

    def parse(self, input_str: str) -> PlatformParseResult:
        url = input_str.strip()
        try:
            import yt_dlp
        except ImportError:
            return PlatformParseResult(
                platform=PlatformType.BILIBILI,
                media_list=[],
                metadata={},
                raw_input=url,
                error="请安装 yt-dlp: pip install yt-dlp",
            )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            return PlatformParseResult(
                platform=PlatformType.BILIBILI,
                media_list=[],
                metadata={},
                raw_input=url,
                error=f"解析失败: {str(e)}",
            )

        if not info:
            return PlatformParseResult(
                platform=PlatformType.BILIBILI,
                media_list=[],
                metadata={},
                raw_input=url,
                error="无法获取视频信息",
            )

        # Prefer original URL for download (yt-dlp handles it in executor)
        video_url = url
        duration = info.get("duration")
        title = info.get("title") or info.get("id", "")
        uploader = info.get("uploader") or info.get("creator") or ""

        metadata = {
            "title": title,
            "author": uploader,
            "duration": duration,
            "id": info.get("id"),
            "bvid": info.get("display_id"),
        }

        return PlatformParseResult(
            platform=PlatformType.BILIBILI,
            media_list=[
                MediaResource(
                    url=video_url,
                    media_type="video",
                    duration_sec=float(duration) if duration else None,
                )
            ],
            metadata=metadata,
            raw_input=url,
        )
