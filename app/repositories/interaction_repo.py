from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.repositories.base import BaseRepository


class InteractionRepository(BaseRepository[Interaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Interaction, db)

    async def get_by_person(self, person_id: str, limit: int = 20) -> list[Interaction]:
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.person_id == person_id)
            .order_by(Interaction.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> list[Interaction]:
        result = await self.db.execute(
            select(Interaction)
            .order_by(Interaction.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
