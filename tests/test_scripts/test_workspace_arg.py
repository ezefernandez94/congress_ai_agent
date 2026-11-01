"""Scripts pick their workspace with --workspace (REQ-024, UC-018, UC-019)."""

import pytest
from sqlalchemy import select

from app.core import tenancy
from app.core.scoping import session_workspace
from app.core.tenancy import WorkspaceChoiceError, find_workspace, workspace_session
from app.models.person import Person


async def test_uc019_workspace_optional_when_only_one(db_session, workspace_a):
    assert (await find_workspace(db_session, None)).id == workspace_a.id


async def test_uc019_workspace_required_when_several(db_session, workspace_a, workspace_b):
    with pytest.raises(WorkspaceChoiceError, match="Workspace A.*Workspace B"):
        await find_workspace(db_session, None)


async def test_uc019_workspace_by_name_or_id(db_session, workspace_a, workspace_b):
    assert (await find_workspace(db_session, "Workspace B")).id == workspace_b.id
    assert (await find_workspace(db_session, workspace_a.id)).id == workspace_a.id


async def test_uc019_unknown_workspace_lists_choices(db_session, workspace_a):
    with pytest.raises(WorkspaceChoiceError, match="No workspace 'Nope'.*Workspace A"):
        await find_workspace(db_session, "Nope")


async def test_uc019_script_session_sees_only_chosen_workspace(
    db_session, workspace_a, workspace_b, as_workspace, use_test_session
):
    db = as_workspace(workspace_b)
    db.add(Person(full_name="Zebra"))
    await db.flush()
    db = as_workspace(workspace_a)
    db.add(Person(full_name="Antelope"))
    await db.flush()
    db_session.info.clear()
    use_test_session(tenancy)

    async with workspace_session("Workspace A") as db:
        names = (await db.execute(select(Person.full_name))).scalars().all()
        assert session_workspace(db) == workspace_a.id

    assert names == ["Antelope"]
