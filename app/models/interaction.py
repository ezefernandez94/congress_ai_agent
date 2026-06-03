import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, InteractionType, NoteSource, Sentiment, TimestampMixin


class Interaction(Base, TimestampMixin):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("people.id"), nullable=False)
    meeting_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("meetings.id"), nullable=True)
    interaction_type: Mapped[InteractionType] = mapped_column(default=InteractionType.conversation)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    raw_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics_discussed: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    commitments_made: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sentiment: Mapped[Sentiment | None] = mapped_column(nullable=True)

    source: Mapped[NoteSource] = mapped_column(default=NoteSource.text)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="interactions")  # noqa: F821
