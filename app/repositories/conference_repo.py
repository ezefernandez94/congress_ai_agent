from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conference import Conference
from app.repositories.base import BaseRepository


class ConferenceRepository(BaseRepository[Conference]):
    def __init__(self, db: AsyncSession):
        super().__init__(Conference, db)

    async def get_active(self) -> Conference | None:
        result = await self.db.execute(
            select(Conference)
            .where(Conference.is_active.is_(True))
            .order_by(Conference.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Conference]:
        result = await self.db.execute(
            select(Conference).order_by(Conference.start_date.desc().nullslast())
        )
        return list(result.scalars().all())

    async def set_active(self, conference_id: str) -> Conference | None:
        """Make one conference active and deactivate every other.

        The agent's context builder always reads whichever row is active, so
        exactly one must be — this clears the flag everywhere first rather
        than trusting the caller to have done it.
        """
        conference = await self.get(conference_id)
        if conference is None:
            return None

        await self.db.execute(
            sa_update(Conference)
            .where(Conference.id != conference_id)
            .values(is_active=False)
        )
        conference.is_active = True
        self.db.add(conference)
        await self.db.flush()
        await self.db.refresh(conference)
        return conference
