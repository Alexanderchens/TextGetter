"""Platform parser base interface."""
from abc import ABC, abstractmethod

from app.parsers.models import PlatformParseResult, PlatformType


class IPlatformParser(ABC):
    """Platform parser interface."""

    @abstractmethod
    def can_handle(self, input_str: str) -> bool:
        """Whether this parser can handle the input."""
        pass

    @abstractmethod
    def parse(self, input_str: str) -> PlatformParseResult:
        """Parse input and return media resources."""
        pass

    @property
    @abstractmethod
    def platform(self) -> PlatformType:
        pass
