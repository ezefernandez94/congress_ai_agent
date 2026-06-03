from datetime import date

from pydantic import BaseModel, ConfigDict


class ConferenceBase(BaseModel):
    name: str
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    goals: list[str] | None = None
    target_contact_types: list[str] | None = None
    is_active: bool = True


class ConferenceCreate(ConferenceBase):
    pass


class ConferenceUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    goals: list[str] | None = None
    target_contact_types: list[str] | None = None
    schedule_imported: bool | None = None
    summary_generated: bool | None = None
    post_conference_report: str | None = None
    is_active: bool | None = None


class ConferenceRead(ConferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    schedule_imported: bool
    summary_generated: bool
    post_conference_report: str | None = None
    created_at: date
    updated_at: date
