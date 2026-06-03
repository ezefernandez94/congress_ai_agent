import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MeetingType, Sentiment, TimestampMixin

meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("meeting_id", UUID(as_uuid=False), ForeignKey("meetings.id"), primary_key=True),
    Column("person_id", UUID(as_uuid=False), ForeignKey("people.id"), primary_key=True),
)


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    meeting_type: Mapped[MeetingType] = mapped_column(default=MeetingType.spontaneous)
    conference_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("conferences.id"), nullable=True)

    prep_brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    talking_points: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    questions_to_ask: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[Sentiment | None] = mapped_column(nullable=True)
    next_steps: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    followed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    followed_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["Person"]] = relationship("Person", secondary=meeting_participants, back_populates="meetings")  # noqa: F821
