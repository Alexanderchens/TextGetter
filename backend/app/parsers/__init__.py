"""Platform parsers."""
from app.parsers.models import PlatformType, MediaResource, PlatformParseResult
from app.parsers.registry import PlatformParserRegistry, get_default_registry
from app.parsers.local_adapter import LocalAdapter
from app.parsers.bilibili_adapter import BilibiliAdapter

__all__ = [
    "PlatformType",
    "MediaResource",
    "PlatformParseResult",
    "PlatformParserRegistry",
    "get_default_registry",
    "LocalAdapter",
    "BilibiliAdapter",
]
