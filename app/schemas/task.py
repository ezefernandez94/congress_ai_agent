from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import TaskPriority, TaskStatus, TaskType


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    task_type: TaskType = TaskType.other
    related_person_id: str | None = None
    related_company_id: str | None = None
    related_meeting_id: str | None = None
    note_id: str | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: date | None = None
    draft_content: str | None = None
    created_by: str = "agent"


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    due_date: date | None = None
    completed_at: datetime | None = None
    draft_content: str | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: TaskStatus
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
