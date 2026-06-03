import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    crunchbase_url: Mapped[str | None] = mapped_column(String, nullable=True)

    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    funding_total: Mapped[int | None] = mapped_column(nullable=True)
    last_funding_date: Mapped[date | None] = mapped_column(nullable=True)
    investor_list: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    relevance_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    strategic_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    company_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recent_news: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    people: Mapped[list["Person"]] = relationship("Person", back_populates="company")  # noqa: F821
