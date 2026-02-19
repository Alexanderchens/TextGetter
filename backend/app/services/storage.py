"""Storage service for media cache."""
from pathlib import Path
from app.config import get_settings


class StorageService:
    """Manage media cache and task working directories."""

    def __init__(self):
        settings = get_settings()
        self.cache_root = Path(settings.data_dir) / "cache"
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def get_task_dir(self, task_id: str) -> Path:
        """Get or create task working directory."""
        path = self.cache_root / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_media_path(self, task_id: str, filename: str = "video") -> Path:
        """Get expected media path for task."""
        return self.get_task_dir(task_id) / filename

    def cleanup_task(self, task_id: str) -> None:
        """Remove task cache directory."""
        path = self.cache_root / task_id
        if path.exists():
            for f in path.iterdir():
                f.unlink()
            path.rmdir()
