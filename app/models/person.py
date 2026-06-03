import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    ContactType,
    FollowUpStatus,
    InterestLevel,
    PriorityTier,
    TimestampMixin,
)


class Person(Base, TimestampMixin):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("companies.id"), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    twitter_handle: Mapped[str | None] = mapped_column(String, nullable=True)

    contact_type: Mapped[ContactType] = mapped_column(default=ContactType.other)
    priority_tier: Mapped[PriorityTier] = mapped_column(default=PriorityTier.unranked)
    interest_level: Mapped[InterestLevel] = mapped_column(default=InterestLevel.unknown)
    warmth_score: Mapped[float] = mapped_column(Float, default=0.5)

    how_met: Mapped[str | None] = mapped_column(String, nullable=True)
    first_interaction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_interaction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    follow_up_status: Mapped[FollowUpStatus] = mapped_column(default=FollowUpStatus.pending)
    next_action: Mapped[str | None] = mapped_column(String, nullable=True)
    next_action_due: Mapped[date | None] = mapped_column(nullable=True)

    linkedin_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrichment_source: Mapped[str | None] = mapped_column(String, nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    company: Mapped["Company | None"] = relationship("Company", back_populates="people")  # noqa: F821
    interactions: Mapped[list["Interaction"]] = relationship("Interaction", back_populates="person")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship("Task", foreign_keys="Task.related_person_id", back_populates="person")  # noqa: F821
    opportunities: Mapped[list["Opportunity"]] = relationship("Opportunity", back_populates="person")  # noqa: F821
    meetings: Mapped[list["Meeting"]] = relationship("Meeting", secondary="meeting_participants", back_populates="participants")  # noqa: F821
