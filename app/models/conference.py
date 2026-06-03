import uuid
from datetime import date

from sqlalchemy import ARRAY, Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conference(Base, TimestampMixin):
    __tablename__ = "conferences"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)

    goals: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    target_contact_types: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    schedule_imported: Mapped[bool] = mapped_column(Boolean, default=False)

    summary_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    post_conference_report: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
