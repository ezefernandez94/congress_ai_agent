import os

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Importing the package registers every model on Base.metadata, not just the base class.
from app.models import Base

# Defaults to the docker compose database published on the host; the app container sets its own
# in-network URL in docker-compose.yml.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5434/conference_bot_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def _ensure_database_exists(url: str) -> None:
    # CREATE DATABASE can't run inside a transaction or against the database being created, so this
    # goes through the maintenance database with a plain asyncpg connection.
    target = make_url(url)
    conn = await asyncpg.connect(
        user=target.username,
        password=target.password,
        host=target.host,
        port=target.port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", target.database)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{target.database}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    await _ensure_database_exists(TEST_DATABASE_URL)
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client():
    from app.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
