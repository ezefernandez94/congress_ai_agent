from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import TaskStatus
from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)

    async def get_pending(
        self,
        priority: str | None = None,
        person_id: str | None = None,
        limit: int = 10,
    ) -> list[Task]:
        stmt = select(Task).where(Task.status == TaskStatus.pending)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if person_id:
            stmt = stmt.where(Task.related_person_id == person_id)
        stmt = stmt.order_by(Task.priority, Task.due_date).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_title(self, title: str) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.title.ilike(f"%{title}%")).limit(1)
        )
        return result.scalar_one_or_none()

    async def complete(self, task: Task) -> Task:
        from datetime import datetime, timezone

        task.status = TaskStatus.completed
        task.completed_at = datetime.now(timezone.utc)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task
