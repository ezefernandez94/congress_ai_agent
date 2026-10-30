from unittest.mock import AsyncMock, MagicMock

import app.bot.auth as bot_auth
from app.bot import router
from app.models.base import WorkspaceRole
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import WorkspaceRepository


def _update(telegram_user_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = telegram_user_id
    update.message.reply_text = AsyncMock()
    return update


def _context(*args: str) -> MagicMock:
    context = MagicMock()
    context.args = list(args)
    return context


async def _owner_in(db_session, telegram_user_id: int, workspace_name: str):
    user = await UserRepository(db_session).ensure_user(telegram_user_id, is_owner=True)
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.create({"name": workspace_name})
    await workspaces.add_member(workspace.id, user.id, WorkspaceRole.admin)
    return workspace


async def test_uc012_adduser_joins_adders_workspace(db_session, use_test_session):
    use_test_session(bot_auth, router)
    workspace = await _owner_in(db_session, 3001, "Acme")

    await router.adduser_command(_update(3001), _context("3002", "Ana"))

    added = await UserRepository(db_session).get_by_telegram_id(3002)
    membership = await WorkspaceRepository(db_session).get_membership(added.id)
    assert membership.workspace_id == workspace.id
    assert membership.role == WorkspaceRole.member


async def test_uc012_adduser_refuses_user_in_other_workspace(db_session, use_test_session):
    use_test_session(bot_auth, router)
    await _owner_in(db_session, 3003, "Acme")
    other = await _owner_in(db_session, 3004, "Globex")
    update = _update(3003)

    await router.adduser_command(update, _context("3004"))

    update.message.reply_text.assert_awaited_once_with("That user belongs to another workspace.")
    owner = await UserRepository(db_session).get_by_telegram_id(3004)
    membership = await WorkspaceRepository(db_session).get_membership(owner.id)
    assert membership.workspace_id == other.id


async def test_uc012_adduser_reenables_revoked_member(db_session, use_test_session):
    use_test_session(bot_auth, router)
    workspace = await _owner_in(db_session, 3005, "Acme")
    users = UserRepository(db_session)
    revoked = await users.ensure_user(3006)
    await WorkspaceRepository(db_session).add_member(workspace.id, revoked.id)
    await users.set_active(3006, False)

    await router.adduser_command(_update(3005), _context("3006"))

    assert (await users.get_by_telegram_id(3006)).is_active
