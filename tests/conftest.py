import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

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
def use_test_session(db_session, monkeypatch):
    """Point code that opens its own session_scope() at the test's session.

    The real session_scope commits to the app database; here every scope reuses db_session,
    so the test sees the writes and they are rolled back when it ends.
    """

    @asynccontextmanager
    async def scope():
        yield db_session
        await db_session.flush()

    def patch(*modules):
        for module in modules:
            monkeypatch.setattr(module, "session_scope", scope)

    return patch


@pytest.fixture
async def client():
    from app.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# --- workspaces (ADR-013, ADR-018) -------------------------------------------------------------


@dataclass
class TestWorkspace:
    """A workspace with one admin, ready to scope a session to."""

    __test__ = False  # not a test class, despite the name

    id: str
    user_id: str
    telegram_user_id: int


async def _make_workspace(db: AsyncSession, name: str, telegram_user_id: int) -> TestWorkspace:
    from app.models.base import WorkspaceRole
    from app.repositories.user_repo import UserRepository
    from app.repositories.workspace_repo import WorkspaceRepository

    user = await UserRepository(db).ensure_user(telegram_user_id, display_name=f"{name} admin")
    workspaces = WorkspaceRepository(db)
    workspace = await workspaces.create({"name": name})
    await workspaces.add_member(workspace.id, user.id, WorkspaceRole.admin)
    return TestWorkspace(id=workspace.id, user_id=user.id, telegram_user_id=telegram_user_id)


@pytest.fixture
async def workspace_a(db_session) -> TestWorkspace:
    return await _make_workspace(db_session, "Workspace A", 900_001)


@pytest.fixture
async def workspace_b(db_session) -> TestWorkspace:
    return await _make_workspace(db_session, "Workspace B", 900_002)


@pytest.fixture
def as_workspace(db_session):
    """Switch db_session to another workspace, the way a fresh request would see the database.

    Both workspaces share one transaction so each can see the other's uncommitted rows at the SQL
    level, which is what a leak test needs. The identity map is cleared on every switch: a real
    session only ever holds one workspace's objects.
    """
    from app.core.scoping import scope_session

    def switch(workspace: TestWorkspace) -> AsyncSession:
        db_session.expunge_all()
        scope_session(db_session, workspace.id, workspace.user_id)
        return db_session

    return switch


@pytest.fixture
async def scoped_db(db_session, workspace_a, as_workspace) -> AsyncSession:
    """db_session scoped to workspace_a, for tests that only need one workspace."""
    return as_workspace(workspace_a)
