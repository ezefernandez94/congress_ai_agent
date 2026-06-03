from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.models.person import Person


class SearchService:
    async def search_contacts(
        self,
        db: AsyncSession,
        query: str,
        contact_type: str | None = None,
        limit: int = 5,
    ) -> list[Person]:
        stmt = select(Person).where(
            or_(
                Person.full_name.ilike(f"%{query}%"),
                Person.notes.ilike(f"%{query}%"),
                Person.bio_snapshot.ilike(f"%{query}%"),
            )
        )
        if contact_type:
            stmt = stmt.where(Person.contact_type == contact_type)
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def search_interactions(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> list[Interaction]:
        result = await db.execute(
            select(Interaction)
            .where(
                or_(
                    Interaction.raw_note.ilike(f"%{query}%"),
                    Interaction.processed_summary.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())


search_service = SearchService()
