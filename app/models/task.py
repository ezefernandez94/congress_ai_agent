import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TaskPriority, TaskStatus, TaskType, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(default=TaskType.other)

    related_person_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("people.id"), nullable=True)
    related_company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("companies.id"), nullable=True)
    related_meeting_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("meetings.id"), nullable=True)
    note_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("notes.id"), nullable=True)

    priority: Mapped[TaskPriority] = mapped_column(default=TaskPriority.medium)
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.pending)
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[str] = mapped_column(String, default="agent")
    draft_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person | None"] = relationship("Person", foreign_keys=[related_person_id], back_populates="tasks")  # noqa: F821
