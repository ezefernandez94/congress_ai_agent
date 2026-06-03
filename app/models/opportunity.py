import uuid
from datetime import date

from sqlalchemy import ARRAY, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, OpportunityStage, OpportunityType, TimestampMixin


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    opportunity_type: Mapped[OpportunityType] = mapped_column(nullable=False)

    person_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("people.id"), nullable=True)
    company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("companies.id"), nullable=True)

    stage: Mapped[OpportunityStage] = mapped_column(default=OpportunityStage.identified)
    estimated_value: Mapped[str | None] = mapped_column(String, nullable=True)
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    expected_close_date: Mapped[date | None] = mapped_column(nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pitch_feedback: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    objections_raised: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    next_step: Mapped[str | None] = mapped_column(String, nullable=True)
    next_step_due: Mapped[date | None] = mapped_column(nullable=True)

    person: Mapped["Person | None"] = relationship("Person", back_populates="opportunities")  # noqa: F821
