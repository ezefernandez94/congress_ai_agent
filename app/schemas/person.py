from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import ContactType, FollowUpStatus, InterestLevel, PriorityTier


class PersonBase(BaseModel):
    full_name: str
    role: str | None = None
    company_id: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    phone: str | None = None
    twitter_handle: str | None = None
    contact_type: ContactType = ContactType.other
    priority_tier: PriorityTier = PriorityTier.unranked
    interest_level: InterestLevel = InterestLevel.unknown
    warmth_score: float = 0.5
    how_met: str | None = None
    notes: str | None = None
    follow_up_status: FollowUpStatus = FollowUpStatus.pending
    next_action: str | None = None
    next_action_due: date | None = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    company_id: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    phone: str | None = None
    contact_type: ContactType | None = None
    priority_tier: PriorityTier | None = None
    interest_level: InterestLevel | None = None
    warmth_score: float | None = None
    how_met: str | None = None
    notes: str | None = None
    follow_up_status: FollowUpStatus | None = None
    next_action: str | None = None
    next_action_due: date | None = None
    linkedin_summary: str | None = None
    bio_snapshot: str | None = None
    enriched_at: datetime | None = None
    enrichment_source: str | None = None
    last_interaction_date: datetime | None = None


class PersonRead(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    linkedin_summary: str | None = None
    bio_snapshot: str | None = None
    enriched_at: datetime | None = None
    enrichment_source: str | None = None
    first_interaction_date: datetime | None = None
    last_interaction_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
