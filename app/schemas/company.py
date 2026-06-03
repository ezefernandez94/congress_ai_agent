from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    name: str
    website: str | None = None
    linkedin_url: str | None = None
    crunchbase_url: str | None = None
    industry: str | None = None
    stage: str | None = None
    funding_total: int | None = None
    last_funding_date: date | None = None
    investor_list: list[str] | None = None
    relevance_tags: list[str] | None = None
    strategic_notes: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    stage: str | None = None
    funding_total: int | None = None
    last_funding_date: date | None = None
    investor_list: list[str] | None = None
    relevance_tags: list[str] | None = None
    strategic_notes: str | None = None
    company_summary: str | None = None
    recent_news: list[dict] | None = None
    enriched_at: datetime | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_summary: str | None = None
    recent_news: list[dict] | None = None
    enriched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
