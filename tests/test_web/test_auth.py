from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.web.auth as web_auth
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import WorkspaceRepository
from app.web.routes import users as users_routes


def _request(telegram_user_id: int | None = None, form: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.session = {web_auth.SESSION_KEY: str(telegram_user_id)} if telegram_user_id else {}
    request.state = SimpleNamespace()
    request.form = AsyncMock(return_value=form or {})
    return request


@pytest.fixture
def production(monkeypatch):
    # The development bypass is skipped only in production (ADR-008).
    monkeypatch.setattr(type(web_auth.settings), "is_production", property(lambda self: True))


async def _member(db_session, telegram_user_id: int, workspace_name: str, is_owner=False):
    user = await UserRepository(db_session).ensure_user(telegram_user_id, is_owner=is_owner)
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.create({"name": workspace_name})
    await workspaces.add_member(workspace.id, user.id)
    return user, workspace


async def test_uc012_web_member_gets_caller(db_session, production):
    user, workspace = await _member(db_session, 4001, "Acme")
    request = _request(4001)

    assert (await web_auth.require_web_user(request, db_session)).id == user.id
    assert request.state.caller.workspace_id == workspace.id


async def test_uc012_web_user_without_membership_redirected_to_login(db_session, production):
    await UserRepository(db_session).ensure_user(4002)
    request = _request(4002)

    with pytest.raises(web_auth.NotLoggedIn) as exc:
        await web_auth.require_web_user(request, db_session)

    assert exc.value.reason == "revoked"
    assert web_auth.SESSION_KEY not in request.session


async def test_uc012_web_db_error_denies(db_session, production, monkeypatch):
    async def broken(db, telegram_user_id):
        raise RuntimeError("database is down")

    monkeypatch.setattr(web_auth, "resolve_caller", broken)

    with pytest.raises(web_auth.NotLoggedIn) as exc:
        await web_auth.require_web_user(_request(4003), db_session)

    assert exc.value.reason == "lookup_failed"


async def test_uc012_web_add_joins_adders_workspace(db_session, production):
    _, workspace = await _member(db_session, 4004, "Acme", is_owner=True)
    request = _request(4004, form={"telegram_user_id": "4005", "display_name": "Ana"})
    owner = await web_auth.require_web_user(request, db_session)

    await users_routes.add(request, db_session, owner)

    added = await UserRepository(db_session).get_by_telegram_id(4005)
    membership = await WorkspaceRepository(db_session).get_membership(added.id)
    assert membership.workspace_id == workspace.id


async def test_uc012_web_add_refuses_user_in_other_workspace(db_session, production):
    await _member(db_session, 4006, "Acme", is_owner=True)
    _, other = await _member(db_session, 4007, "Globex")
    request = _request(4006, form={"telegram_user_id": "4007"})
    owner = await web_auth.require_web_user(request, db_session)

    response = await users_routes.add(request, db_session, owner)

    assert response.headers["location"] == "/users?error=That%20user%20belongs%20to%20another%20workspace"
    other_user = await UserRepository(db_session).get_by_telegram_id(4007)
    assert (await WorkspaceRepository(db_session).get_membership(other_user.id)).workspace_id == other.id
