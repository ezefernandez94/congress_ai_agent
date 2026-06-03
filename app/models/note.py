import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NoteSource, TimestampMixin


class Note(Base, TimestampMixin):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("people.id"), nullable=True)
    meeting_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("meetings.id"), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[NoteSource] = mapped_column(default=NoteSource.text)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
