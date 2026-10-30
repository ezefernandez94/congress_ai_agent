from unittest.mock import MagicMock

import app.bot.auth as bot_auth
from app.models.base import WorkspaceRole
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import DEFAULT_WORKSPACE_NAME, WorkspaceRepository


def _update(telegram_user_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = telegram_user_id
    return update


async def test_uc012_authorize_returns_caller(db_session, use_test_session):
    use_test_session(bot_auth)
    user = await UserRepository(db_session).ensure_user(2001)
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.create({"name": "Acme"})
    await workspaces.add_member(workspace.id, user.id)

    caller = await bot_auth.authorize(_update(2001))

    assert caller is not None
    assert caller.user.id == user.id
    assert caller.workspace_id == workspace.id
    assert caller.role == WorkspaceRole.member


async def test_uc012_authorize_without_membership_denies(db_session, use_test_session):
    use_test_session(bot_auth)
    await UserRepository(db_session).ensure_user(2002)

    assert await bot_auth.authorize(_update(2002)) is None


async def test_uc012_authorize_db_error_denies(monkeypatch):
    async def broken(db, telegram_user_id):
        raise RuntimeError("database is down")

    monkeypatch.setattr(bot_auth, "resolve_caller", broken)

    assert await bot_auth.authorize(_update(2003)) is None


async def test_uc012_seeded_owner_becomes_admin_of_default(db_session, use_test_session, monkeypatch):
    use_test_session(bot_auth)
    monkeypatch.setattr(type(bot_auth.settings), "allowed_user_ids", property(lambda self: {2004}))

    await bot_auth.seed_users_from_env()

    caller = await bot_auth.authorize(_update(2004))
    assert caller is not None
    assert caller.user.is_owner
    assert caller.role == WorkspaceRole.admin
    default = await WorkspaceRepository(db_session).get(caller.workspace_id)
    assert default.name == DEFAULT_WORKSPACE_NAME


async def test_uc012_seeding_keeps_existing_membership(db_session, use_test_session, monkeypatch):
    use_test_session(bot_auth)
    monkeypatch.setattr(type(bot_auth.settings), "allowed_user_ids", property(lambda self: {2005}))
    user = await UserRepository(db_session).ensure_user(2005)
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.create({"name": "Acme"})
    await workspaces.add_member(workspace.id, user.id)

    await bot_auth.seed_users_from_env()

    caller = await bot_auth.authorize(_update(2005))
    assert caller.workspace_id == workspace.id
