from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.base import OpportunityStage, OpportunityType


class OpportunityBase(BaseModel):
    title: str
    opportunity_type: OpportunityType
    person_id: str | None = None
    company_id: str | None = None
    stage: OpportunityStage = OpportunityStage.identified
    estimated_value: str | None = None
    probability: float = 0.5
    expected_close_date: date | None = None
    notes: str | None = None
    pitch_feedback: list[str] | None = None
    objections_raised: list[str] | None = None
    next_step: str | None = None
    next_step_due: date | None = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    stage: OpportunityStage | None = None
    estimated_value: str | None = None
    probability: float | None = None
    expected_close_date: date | None = None
    notes: str | None = None
    pitch_feedback: list[str] | None = None
    objections_raised: list[str] | None = None
    next_step: str | None = None
    next_step_due: date | None = None


class OpportunityRead(OpportunityBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: date
    updated_at: date
