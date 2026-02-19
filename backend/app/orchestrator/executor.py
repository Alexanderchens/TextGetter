"""Task execution logic."""
import asyncio
from pathlib import Path
from typing import Optional

from app.database import async_session
from app.extractors.pipeline import ExtractPipeline
from app.models.task import TaskStatus
from app.parsers import get_default_registry
from app.parsers.models import UnsupportedPlatformError
from app.repositories.task_repository import TaskRepository, TaskResultRepository
from app.services.storage import StorageService


async def _update_progress(
    task_id: str,
    status: str,
    progress: Optional[int] = None,
    stage_progress: Optional[dict] = None,
    error: Optional[str] = None,
):
    """Update task progress in DB."""
    async with async_session() as session:
        repo = TaskRepository(session)
        await repo.update_status(
            task_id,
            status=status,
            progress=progress,
            stage_progress=stage_progress,
            error=error,
        )
        await session.commit()




async def execute_task(task_id: str) -> None:
    """Execute extraction task. Runs in background."""
    storage = StorageService()
    registry = get_default_registry()
    pipeline = ExtractPipeline()

    async with async_session() as session:
        task_repo = TaskRepository(session)
        result_repo = TaskResultRepository(session)
        task = await task_repo.get(task_id)

    if not task:
        return

    if task.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value, TaskStatus.FAILED.value):
        return

    try:
        # 1. PARSING
        await _update_progress(
            task_id,
            status=TaskStatus.PARSING.value,
            progress=5,
            stage_progress={"parsing": {"status": "running", "progress": 0}},
        )
        parse_result = registry.parse(task.input)

        if parse_result.error:
            await _update_progress(task_id, status=TaskStatus.FAILED.value, error=parse_result.error)
            return

        # Update task platform/metadata
        async with async_session() as session:
            task_repo = TaskRepository(session)
            t = await task_repo.get(task_id)
            if t:
                t.platform = parse_result.platform.value
                t.metadata_ = parse_result.metadata
                await task_repo.update(t)
                await session.commit()

        media = parse_result.media_list[0]
        media_path = media.local_path

        # 2. DOWNLOADING (for local, just ensure we have path; for remote would download)
        await _update_progress(
            task_id,
            status=TaskStatus.DOWNLOADING.value,
            progress=10,
            stage_progress={"downloading": {"status": "running", "progress": 0}},
        )

        if media.url:
            # Remote: download to cache (yt-dlp) with subtitles
            try:
                import yt_dlp
                task_dir = storage.get_task_dir(task_id)
                out_path = task_dir / "video.%(ext)s"
                ydl_opts = {
                    "outtmpl": str(out_path),
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["zh", "zh-Hans", "zh-CN", "en"],
                    "subtitlesformat": "vtt/srt/best",
                    "quiet": True,
                }
                yt_dlp.YoutubeDL(ydl_opts).download([media.url])
                files = list(task_dir.glob("video.*"))
                video_files = [f for f in files if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".flv", ".m4a")]
                media_path = str(video_files[0]) if video_files else (str(files[0]) if files else None)
            except Exception as e:
                await _update_progress(task_id, status=TaskStatus.FAILED.value, error=f"下载失败: {e}")
                return
        else:
            # Local: copy to cache for consistency (optional, could use directly)
            # Using directly to avoid disk duplication for local files
            pass

        if not media_path or not Path(media_path).exists():
            await _update_progress(task_id, status=TaskStatus.FAILED.value, error="无法获取媒体文件")
            return

        # 3. EXTRACTING
        await _update_progress(
            task_id,
            status=TaskStatus.EXTRACTING.value,
            progress=15,
            stage_progress={
                "subtitle": {"status": "pending", "progress": 0},
                "asr": {"status": "pending", "progress": 0},
                "merge": {"status": "pending", "progress": 0},
            },
        )

        # Run extraction (sync - run in executor to not block event loop)
        loop = asyncio.get_event_loop()
        merged = await loop.run_in_executor(None, lambda: pipeline.run(media_path))

        # 4. SAVE RESULT & COMPLETE
        async with async_session() as session:
            task_repo = TaskRepository(session)
            result_repo = TaskResultRepository(session)

            segments_dict = [s.to_dict() for s in merged.segments]
            await result_repo.save(
                task_id,
                full_text=merged.full_text,
                segments=segments_dict,
                stats=merged.stats,
            )
            await task_repo.update_status(
                task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                stage_progress={
                    "parsing": {"status": "done", "progress": 100},
                    "downloading": {"status": "done", "progress": 100},
                    "subtitle": {"status": "done", "progress": 100},
                    "asr": {"status": "done", "progress": 100},
                    "merge": {"status": "done", "progress": 100},
                },
            )
            await session.commit()

        # Cleanup cache for remote (optional)
        if media.url:
            storage.cleanup_task(task_id)

    except UnsupportedPlatformError as e:
        await _update_progress(task_id, status=TaskStatus.FAILED.value, error=str(e.message))
    except Exception as e:
        await _update_progress(task_id, status=TaskStatus.FAILED.value, error=str(e))
        raise
