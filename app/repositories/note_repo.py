from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    def __init__(self, db: AsyncSession):
        super().__init__(Note, db)

    async def get_by_person(self, person_id: str, limit: int = 20) -> list[Note]:
        result = await self.db.execute(
            select(Note)
            .where(Note.person_id == person_id)
            .order_by(Note.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unprocessed(self, limit: int = 20) -> list[Note]:
        result = await self.db.execute(
            select(Note)
            .where(Note.processed.is_(False))
            .order_by(Note.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
