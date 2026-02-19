"""Task API endpoints."""
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.database import async_session
from app.models.task import Task, TaskResult, TaskStatus
from app.repositories.task_repository import TaskRepository, TaskResultRepository
from app.orchestrator import execute_task


router = APIRouter()


class CreateTaskRequest(BaseModel):
    input: str
    options: Optional[dict] = None


class CreateTaskResponse(BaseModel):
    taskId: str
    status: str
    message: str


def _task_to_response(task: Task, result: Optional[TaskResult] = None) -> dict:
    """Convert Task to API response format."""
    data = {
        "id": task.id,
        "input": task.input,
        "platform": task.platform,
        "status": task.status,
        "progress": task.progress or 0,
        "stageProgress": task.stage_progress or {},
        "metadata": task.metadata_ or {},
        "error": task.error,
        "result": None,
        "createdAt": task.created_at.isoformat() + "Z" if task.created_at else None,
        "updatedAt": task.updated_at.isoformat() + "Z" if task.updated_at else None,
    }
    if result:
        segments = result.segments.get("items", []) if isinstance(result.segments, dict) else result.segments
        data["result"] = {
            "fullText": result.full_text,
            "segments": segments,
            "stats": result.stats or {},
        }
    return data


@router.post("", response_model=CreateTaskResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
):
    """Create extraction task."""
    from app.database import async_session
    from app.models.task import Task

    async with async_session() as session:
        repo = TaskRepository(session)
        task = Task(
            input=request.input,
            platform="unknown",
            status=TaskStatus.PENDING.value,
        )
        await repo.create(task)
        await session.commit()
        task_id = task.id

    background_tasks.add_task(execute_task, task_id)

    return CreateTaskResponse(
        taskId=task_id,
        status="pending",
        message="任务已创建",
    )


@router.post("/upload", response_model=CreateTaskResponse)
async def create_task_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[str] = Form(None),
):
    """Create task from uploaded file."""
    import uuid
    from pathlib import Path

    from app.models.task import Task
    from app.services.storage import StorageService

    task_id = str(uuid.uuid4())
    storage = StorageService()
    task_dir = storage.get_task_dir(task_id)
    ext = Path(file.filename or "video").suffix or ".mp4"
    save_path = task_dir / f"video{ext}"
    content = await file.read()
    save_path.write_bytes(content)

    async with async_session() as session:
        repo = TaskRepository(session)
        task = Task(
            id=task_id,
            input=str(save_path),
            platform="local",
            status=TaskStatus.PENDING.value,
        )
        await repo.create(task)
        await session.commit()

    background_tasks.add_task(execute_task, task_id)

    return CreateTaskResponse(
        taskId=task_id,
        status="pending",
        message="文件已上传，任务已创建",
    )


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get task detail."""
    async with async_session() as session:
        repo = TaskRepository(session)
        result_repo = TaskResultRepository(session)
        task = await repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        result = await result_repo.get(task_id)
        return _task_to_response(task, result)


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            raise HTTPException(status_code=400, detail="任务已结束，无法取消")
        await repo.update_status(task_id, status=TaskStatus.CANCELLED.value)
        await session.commit()
    return {"message": "已取消"}


@router.get("/{task_id}/export")
async def export_task(task_id: str, format: str = "markdown"):
    """Export task result."""
    async with async_session() as session:
        result_repo = TaskResultRepository(session)
        result = await result_repo.get(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="任务或结果不存在")
        if format == "txt":
            return {"content": result.full_text, "format": "txt"}
        return {"content": result.full_text, "format": "markdown"}


@router.get("")
async def list_tasks(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List tasks."""
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks, total = await repo.list(platform=platform, status=status, limit=limit, offset=offset)
        items = [_task_to_response(t) for t in tasks]
        return {"items": items, "total": total}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete task."""
    from app.services.storage import StorageService

    async with async_session() as session:
        repo = TaskRepository(session)
        result_repo = TaskResultRepository(session)
        task = await repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        await result_repo.delete(task_id)
        await repo.delete(task_id)
        await session.commit()

    StorageService().cleanup_task(task_id)
    return {"message": "已删除"}
