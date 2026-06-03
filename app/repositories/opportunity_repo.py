from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.repositories.base import BaseRepository


class OpportunityRepository(BaseRepository[Opportunity]):
    def __init__(self, db: AsyncSession):
        super().__init__(Opportunity, db)

    async def get_by_stage(self, stage: str, limit: int = 20) -> list[Opportunity]:
        result = await self.db.execute(
            select(Opportunity).where(Opportunity.stage == stage).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(self, opportunity_type: str, limit: int = 20) -> list[Opportunity]:
        result = await self.db.execute(
            select(Opportunity)
            .where(Opportunity.opportunity_type == opportunity_type)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_person(self, person_id: str) -> list[Opportunity]:
        result = await self.db.execute(
            select(Opportunity).where(Opportunity.person_id == person_id)
        )
        return list(result.scalars().all())
