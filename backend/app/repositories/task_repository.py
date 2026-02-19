"""Task and TaskResult repository."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskResult, TaskStatus


class TaskRepository:
    """Task CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: Task) -> Task:
        """Create a task."""
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def update(self, task: Task) -> Task:
        """Update task."""
        task.updated_at = datetime.utcnow()
        await self.session.merge(task)
        await self.session.flush()
        return task

    async def update_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        stage_progress: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update task status and related fields."""
        values = {"status": status, "updated_at": datetime.utcnow()}
        if progress is not None:
            values["progress"] = progress
        if stage_progress is not None:
            values["stage_progress"] = stage_progress
        if error is not None:
            values["error"] = error
        await self.session.execute(update(Task).where(Task.id == task_id).values(**values))
        await self.session.flush()

    async def list(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """List tasks with optional filters."""
        query = select(Task)
        count_query = select(func.count()).select_from(Task)

        if platform:
            query = query.where(Task.platform == platform)
            count_query = count_query.where(Task.platform == platform)
        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)

        total = (await self.session.execute(count_query)).scalar() or 0
        query = query.order_by(desc(Task.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        tasks = list(result.scalars().all())
        return tasks, total

    async def delete(self, task_id: str) -> bool:
        """Delete a task."""
        result = await self.session.execute(delete(Task).where(Task.id == task_id))
        await self.session.flush()
        return result.rowcount > 0


class TaskResultRepository:
    """TaskResult CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, task_id: str, full_text: str, segments: list, stats: Optional[dict] = None) -> TaskResult:
        """Save extraction result."""
        result = TaskResult(
            task_id=task_id,
            full_text=full_text,
            segments={"items": segments},
            stats=stats,
        )
        self.session.add(result)
        await self.session.flush()
        return result

    async def get(self, task_id: str) -> Optional[TaskResult]:
        """Get result by task ID."""
        result = await self.session.execute(select(TaskResult).where(TaskResult.task_id == task_id))
        return result.scalar_one_or_none()

    async def delete(self, task_id: str) -> bool:
        """Delete result by task ID."""
        result = await self.session.execute(delete(TaskResult).where(TaskResult.task_id == task_id))
        await self.session.flush()
        return result.rowcount > 0
