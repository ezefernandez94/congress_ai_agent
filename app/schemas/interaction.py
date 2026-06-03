from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import InteractionType, NoteSource, Sentiment


class InteractionBase(BaseModel):
    person_id: str
    meeting_id: str | None = None
    interaction_type: InteractionType = InteractionType.conversation
    occurred_at: datetime | None = None
    raw_note: str | None = None
    processed_summary: str | None = None
    topics_discussed: list[str] | None = None
    commitments_made: list[dict] | None = None
    sentiment: Sentiment | None = None
    source: NoteSource = NoteSource.text
    transcription: str | None = None


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    processed_summary: str | None = None
    topics_discussed: list[str] | None = None
    commitments_made: list[dict] | None = None
    sentiment: Sentiment | None = None


class InteractionRead(InteractionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
