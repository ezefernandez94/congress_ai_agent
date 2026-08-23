from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import NoteSource


class NoteBase(BaseModel):
    person_id: str | None = None
    meeting_id: str | None = None
    raw_content: str
    content_type: NoteSource = NoteSource.text
    transcription: str | None = None
    processed: bool = False


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    person_id: str | None = None
    meeting_id: str | None = None
    raw_content: str | None = None
    content_type: NoteSource | None = None
    transcription: str | None = None
    processed: bool | None = None


class NoteRead(NoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
