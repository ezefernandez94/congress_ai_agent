from app.core.tenancy import resolve_caller
from app.models.base import WorkspaceRole
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import WorkspaceRepository


async def test_uc012_member_resolves_to_workspace(db_session):
    user = await UserRepository(db_session).ensure_user(1001)
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.create({"name": "Acme"})
    await workspaces.add_member(workspace.id, user.id, WorkspaceRole.admin)

    caller = await resolve_caller(db_session, 1001)

    assert caller is not None
    assert caller.user.id == user.id
    assert caller.workspace_id == workspace.id
    assert caller.role == WorkspaceRole.admin


async def test_uc012_user_without_membership_denied(db_session):
    await UserRepository(db_session).ensure_user(1002)

    assert await resolve_caller(db_session, 1002) is None


async def test_uc012_unknown_user_denied(db_session):
    assert await resolve_caller(db_session, 1003) is None


async def test_uc012_inactive_member_denied(db_session):
    users = UserRepository(db_session)
    user = await users.ensure_user(1004)
    workspace = await WorkspaceRepository(db_session).get_or_create_default()
    await WorkspaceRepository(db_session).add_member(workspace.id, user.id)
    await users.set_active(1004, False)

    assert await resolve_caller(db_session, 1004) is None
