import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def generate_uuid() -> str:
        return str(uuid.uuid4())


class WorkspaceScoped:
    """A record that belongs to exactly one workspace (ADR-013) and remembers its creator (REQ-027).

    Every model with this mixin is filtered to the session's workspace and stamped on insert by the
    hooks in app/core/tenancy.py (ADR-018), so code above the models never filters by hand.
    """

    @declared_attr
    def workspace_id(cls) -> Mapped[str]:
        # RESTRICT, not CASCADE: deleting an organization's data is an explicit operation (REQ-036),
        # never the side effect of one stray DELETE on workspaces.
        return mapped_column(
            UUID(as_uuid=False),
            ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def created_by_user_id(cls) -> Mapped[str | None]:
        # Nullable: rows from before multi-workspace have no known creator, and removing a user
        # must not delete what they captured for their organization.
        return mapped_column(
            UUID(as_uuid=False),
            ForeignKey("bot_users.id", ondelete="SET NULL"),
            nullable=True,
        )

class ContactType(str, Enum):
    investor = "investor"
    customer = "customer"
    partner = "partner"
    founder = "founder"
    speaker = "speaker"
    other = "other"

class PriorityTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    unranked = "unranked"

class InterestLevel(str, Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"
    unknown = "unknown"

class FollowUpStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    not_needed = "not_needed"

class TaskType(str, Enum):
    send_email = "send_email"
    send_deck = "send_deck"
    schedule_meeting = "schedule_meeting"
    linkedin_connect = "linkedin_connect"
    research = "research"
    follow_up = "follow_up"
    other = "other"

class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class TaskPriority(str, Enum):
    urgent = "urgent"
    high = "high"
    medium = "medium"
    low = "low"

class Sentiment(str, Enum):
    very_positive = "very_positive"
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class OpportunityType(str, Enum):
    investment = "investment"
    customer = "customer"
    partnership = "partnership"
    co_founder = "co_founder"
    advisor = "advisor"
    press = "press"

class OpportunityStage(str, Enum):
    identified = "identified"
    contacted = "contacted"
    interested = "interested"
    proposal_sent = "proposal_sent"
    negotiating = "negotiating"
    closed_won = "closed_won"
    closed_lost = "closed_lost"
    nurture = "nurture"

class MeetingType(str, Enum):
    pitch = "pitch"
    intro = "intro"
    casual = "casual"
    panel = "panel"
    coffee = "coffee"
    scheduled = "scheduled"
    spontaneous = "spontaneous"

class InteractionType(str, Enum):
    conversation = "conversation"
    pitch = "pitch"
    email = "email"
    linkedin_message = "linkedin_message"
    introduction = "introduction"
    follow_up = "follow_up"

class NoteSource(str, Enum):
    voice = "voice"
    text = "text"


class WorkspaceRole(str, Enum):
    admin = "admin"
    member = "member"
