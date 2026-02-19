"""Configuration management."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App
    app_name: str = "TextGetter"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/textgetter.db"

    # Storage
    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./data/cache")
    retention_days: int = 7

    # Extract
    asr_model: str = "base"  # whisper model: tiny, base, small, medium, large-v3
    ocr_interval: float = 1.0  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()
