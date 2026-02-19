"""Platform parser registry and dispatcher."""
from typing import List, Tuple

from app.parsers.base import IPlatformParser
from app.parsers.local_adapter import is_local_file
from app.parsers.models import PlatformParseResult, UnsupportedPlatformError


class PlatformParserRegistry:
    """Registry for platform parsers. Dispatches to correct parser."""

    def __init__(self):
        self._parsers: List[Tuple[int, IPlatformParser]] = []

    def register(self, parser: IPlatformParser, priority: int = 0) -> None:
        """Register a parser. Higher priority runs first."""
        self._parsers.append((priority, parser))
        self._parsers.sort(key=lambda x: -x[0])

    def parse(self, input_str: str) -> PlatformParseResult:
        """Parse input and return result."""
        if is_local_file(input_str):
            for _, parser in self._parsers:
                if parser.can_handle(input_str):
                    return parser.parse(input_str)
            raise UnsupportedPlatformError("无法处理该本地文件")
        else:
            for _, parser in self._parsers:
                if parser.can_handle(input_str):
                    return parser.parse(input_str)
            raise UnsupportedPlatformError(f"不支持的链接: {input_str[:80]}...")


def get_default_registry() -> PlatformParserRegistry:
    """Get registry with default adapters."""
    from app.parsers.local_adapter import LocalAdapter
    from app.parsers.bilibili_adapter import BilibiliAdapter

    registry = PlatformParserRegistry()
    registry.register(LocalAdapter(), priority=100)
    registry.register(BilibiliAdapter(), priority=90)
    return registry
