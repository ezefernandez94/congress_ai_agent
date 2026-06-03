from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.person import Person
from app.repositories.base import BaseRepository


class PersonRepository(BaseRepository[Person]):
    def __init__(self, db: AsyncSession):
        super().__init__(Person, db)

    async def search_by_name(self, query: str, limit: int = 10) -> list[Person]:
        result = await self.db.execute(
            select(Person)
            .where(Person.full_name.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(self, query: str, contact_type: str | None = None, limit: int = 5) -> list[Person]:
        stmt = select(Person).where(
            or_(
                Person.full_name.ilike(f"%{query}%"),
                Person.notes.ilike(f"%{query}%"),
            )
        )
        if contact_type:
            stmt = stmt.where(Person.contact_type == contact_type)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_linkedin_url(self, url: str) -> Person | None:
        result = await self.db.execute(select(Person).where(Person.linkedin_url == url))
        return result.scalar_one_or_none()

    async def get_recent(self, hours: int = 24, limit: int = 20) -> list[Person]:
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            select(Person)
            .where(Person.created_at >= cutoff)
            .order_by(Person.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
