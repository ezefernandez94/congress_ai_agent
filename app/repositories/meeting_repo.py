from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meeting import Meeting
from app.models.person import Person
from app.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    def __init__(self, db: AsyncSession):
        super().__init__(Meeting, db)

    async def get_with_participants(self, meeting_id: str) -> Meeting | None:
        return await self.get_with(meeting_id, selectinload(Meeting.participants))

    async def set_participants(self, meeting: Meeting, person_ids: list[str]) -> Meeting:
        """Replace the meeting's participant set with exactly these people.

        The M2M is edited as a whole from a multi-select, so this is a
        replace rather than an add/remove pair.
        """
        # participants may not be loaded on an object fetched without the
        # selectinload — touching it lazily would raise MissingGreenlet.
        await self.db.refresh(meeting, ["participants"])

        if person_ids:
            result = await self.db.execute(select(Person).where(Person.id.in_(person_ids)))
            people = list(result.scalars().all())
        else:
            people = []

        meeting.participants = people
        self.db.add(meeting)
        await self.db.flush()
        return meeting

    async def get_by_person(self, person_id: str, limit: int = 20) -> list[Meeting]:
        result = await self.db.execute(
            select(Meeting)
            .join(Meeting.participants)
            .where(Person.id == person_id)
            .order_by(Meeting.scheduled_at.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().unique().all())
