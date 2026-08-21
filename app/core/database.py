from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=not settings.is_production,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Session that commits on clean exit and rolls back on error.

    Use this instead of AsyncSessionLocal() directly for any code path that
    writes. A bare AsyncSessionLocal() rolls back when it closes, and the
    repositories only flush, so writes are silently discarded on exit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with session_scope() as session:
        yield session
