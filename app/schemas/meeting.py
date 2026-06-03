from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import MeetingType, Sentiment


class MeetingBase(BaseModel):
    title: str
    scheduled_at: datetime | None = None
    duration_minutes: int = 30
    location: str | None = None
    meeting_type: MeetingType = MeetingType.spontaneous
    conference_id: str | None = None
    talking_points: list[str] | None = None
    questions_to_ask: list[str] | None = None


class MeetingCreate(MeetingBase):
    participant_ids: list[str] = []


class MeetingUpdate(BaseModel):
    title: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    meeting_type: MeetingType | None = None
    prep_brief: str | None = None
    talking_points: list[str] | None = None
    questions_to_ask: list[str] | None = None
    outcome_summary: str | None = None
    sentiment: Sentiment | None = None
    next_steps: list[str] | None = None
    followed_up: bool | None = None
    followed_up_at: datetime | None = None


class MeetingRead(MeetingBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prep_brief: str | None = None
    outcome_summary: str | None = None
    sentiment: Sentiment | None = None
    next_steps: list[str] | None = None
    followed_up: bool
    followed_up_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
