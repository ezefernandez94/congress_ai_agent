import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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