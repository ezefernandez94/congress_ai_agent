from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: AsyncSession):
        super().__init__(Company, db)

    async def get_by_name(self, name: str) -> Company | None:
        result = await self.db.execute(
            select(Company).where(Company.name.ilike(name))
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str) -> tuple[Company, bool]:
        existing = await self.get_by_name(name)
        if existing:
            return existing, False
        company = await self.create({"name": name})
        return company, True
