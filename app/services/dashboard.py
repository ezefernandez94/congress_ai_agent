"""Aggregations behind the web dashboard.

Reads only — every number here links through to the filtered list page that
explains it.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import InterestLevel, OpportunityStage, TaskStatus
from app.models.company import Company
from app.models.conference import Conference
from app.models.interaction import Interaction
from app.models.opportunity import Opportunity
from app.models.person import Person
from app.models.task import Task
from app.services.digest import DigestData, digest_service


@dataclass
class StageBucket:
    stage: OpportunityStage
    count: int
    weighted: float  # sum of probabilities — a count discounted by confidence


@dataclass
class DashboardData:
    conference: Conference | None
    digest: DigestData

    total_people: int = 0
    total_companies: int = 0
    total_interactions: int = 0
    total_opportunities: int = 0
    pending_tasks: int = 0
    overdue_tasks: int = 0

    by_tier: list[tuple[str, int]] = field(default_factory=list)
    by_contact_type: list[tuple[str, int]] = field(default_factory=list)
    pipeline: list[StageBucket] = field(default_factory=list)

    hot_contacts: list[Person] = field(default_factory=list)
    recent_interactions: list[Interaction] = field(default_factory=list)
    recent_people: list[Person] = field(default_factory=list)

    @property
    def max_tier(self) -> int:
        return max((n for _, n in self.by_tier), default=1) or 1

    @property
    def max_type(self) -> int:
        return max((n for _, n in self.by_contact_type), default=1) or 1


async def _count(db: AsyncSession, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    if where:
        stmt = stmt.where(*where)
    return int((await db.execute(stmt)).scalar_one())


async def _group_count(db: AsyncSession, column) -> list[tuple[str, int]]:
    result = await db.execute(
        select(column, func.count()).group_by(column).order_by(func.count().desc())
    )
    return [(str(getattr(k, "value", k)), int(n)) for k, n in result.all()]


async def collect_dashboard(db: AsyncSession) -> DashboardData:
    today = date.today()

    conference = (
        await db.execute(
            select(Conference)
            .where(Conference.is_active.is_(True))
            .order_by(Conference.created_at.desc())
            .limit(1)
        )
    ).scalars().first()

    digest = await digest_service.collect(db)

    pipeline_rows = await db.execute(
        select(Opportunity.stage, func.count(), func.coalesce(func.sum(Opportunity.probability), 0.0))
        .group_by(Opportunity.stage)
    )
    counts = {stage: (n, float(w)) for stage, n, w in pipeline_rows.all()}
    pipeline = [
        StageBucket(stage=stage, count=counts.get(stage, (0, 0.0))[0], weighted=counts.get(stage, (0, 0.0))[1])
        for stage in OpportunityStage
    ]

    hot = (
        await db.execute(
            select(Person)
            .options(selectinload(Person.company))
            .where(Person.interest_level == InterestLevel.hot)
            .order_by(Person.last_interaction_date.desc().nullslast())
            .limit(8)
        )
    ).scalars().all()

    recent_interactions = (
        await db.execute(
            select(Interaction)
            .options(selectinload(Interaction.person))
            .order_by(Interaction.occurred_at.desc())
            .limit(8)
        )
    ).scalars().all()

    recent_people = (
        await db.execute(
            select(Person)
            .options(selectinload(Person.company))
            .order_by(Person.created_at.desc())
            .limit(8)
        )
    ).scalars().all()

    return DashboardData(
        conference=conference,
        digest=digest,
        total_people=await _count(db, Person),
        total_companies=await _count(db, Company),
        total_interactions=await _count(db, Interaction),
        total_opportunities=await _count(db, Opportunity),
        pending_tasks=await _count(db, Task, Task.status == TaskStatus.pending),
        overdue_tasks=await _count(
            db, Task, Task.status == TaskStatus.pending, Task.due_date < today
        ),
        by_tier=await _group_count(db, Person.priority_tier),
        by_contact_type=await _group_count(db, Person.contact_type),
        pipeline=pipeline,
        hot_contacts=list(hot),
        recent_interactions=list(recent_interactions),
        recent_people=list(recent_people),
    )
