from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: str) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_fields(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        """Assign every key in obj_in, including the ones set to None.

        update() deliberately skips None so the agent can send a sparse dict
        without wiping fields it had no opinion about. An edit form is the
        opposite case: a cleared input means "make this empty", so it needs a
        write path that can actually null a column.
        """
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: str) -> bool:
        obj = await self.get(id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True

    async def count(self, *where: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(self.model)
        if where:
            stmt = stmt.where(*where)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def list_page(
        self,
        *,
        where: Sequence[ColumnElement[bool]] = (),
        order_by: Sequence[Any] = (),
        options: Sequence[Any] = (),
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ModelType], int]:
        """One filtered, ordered, paginated page plus the unpaginated total.

        Callers build the `where` clauses from their own column maps, so the
        SQL stays in this layer while each entity keeps its own filter shape.
        `options` carries the selectinload()s the caller's template needs —
        the session is async, so any relationship a template touches must be
        eager-loaded here or it raises MissingGreenlet during rendering.
        """
        stmt: Select[tuple[ModelType]] = select(self.model)
        if where:
            stmt = stmt.where(*where)
        if options:
            stmt = stmt.options(*options)
        if order_by:
            stmt = stmt.order_by(*order_by)

        result = await self.db.execute(stmt.offset(skip).limit(limit))
        rows = list(result.scalars().unique().all())
        total = await self.count(*where)
        return rows, total

    async def get_with(self, id: str, *options: Any) -> ModelType | None:
        """get() with eager loading, for detail pages that render relationships."""
        stmt = select(self.model).where(self.model.id == id)
        if options:
            stmt = stmt.options(*options)
        result = await self.db.execute(stmt)
        return result.scalars().unique().one_or_none()


def ilike_any(term: str, *columns: InstrumentedAttribute) -> ColumnElement[bool]:
    """OR of `col ILIKE %term%` across the given columns."""
    from sqlalchemy import or_

    pattern = f"%{term}%"
    return or_(*[col.ilike(pattern) for col in columns])
