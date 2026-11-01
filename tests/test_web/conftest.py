"""Web fixtures: two seeded workspaces and a client signed in to workspace A."""

import pytest
from fastapi import Request

from app.core.database import get_db
from app.core.tenancy import resolve_caller
from app.models.company import Company
from app.models.conference import Conference
from app.models.interaction import Interaction
from app.models.meeting import Meeting
from app.models.note import Note
from app.models.opportunity import Opportunity
from app.models.person import Person
from app.models.task import Task
from app.web.auth import require_web_user

MARK_B = "Zebra"
MARK_A = "Antelope"


async def _seed(db, mark: str) -> dict[str, str]:
    company = Company(name=f"{mark} Corp")
    db.add(company)
    db.add(conference := Conference(name=f"{mark} Summit", is_active=False))
    await db.flush()
    person = Person(full_name=f"{mark} Person", company_id=company.id)
    db.add(person)
    await db.flush()
    rows = {
        "companies": company,
        "conferences": conference,
        "people": person,
        "tasks": Task(title=f"{mark} task", related_person_id=person.id),
        "opportunities": Opportunity(title=f"{mark} deal", opportunity_type="investment",
                                     person_id=person.id),
        "interactions": Interaction(person_id=person.id, raw_note=f"{mark} talk"),
        "meetings": Meeting(title=f"{mark} meeting"),
        "notes": Note(raw_content=f"{mark} note", person_id=person.id),
    }
    db.add_all(rows.values())
    await db.flush()
    return {slug: row.id for slug, row in rows.items()}


@pytest.fixture
async def web(db_session, workspace_a, workspace_b, as_workspace, client):
    """Seed both workspaces, then sign the client in as workspace A's admin."""
    from app.api.main import app

    ids_b = await _seed(as_workspace(workspace_b), MARK_B)
    ids_a = await _seed(as_workspace(workspace_a), MARK_A)
    db_session.info.clear()  # get_scoped_db must do the scoping, not the fixture
    caller = await resolve_caller(db_session, workspace_a.telegram_user_id)

    async def signed_in_as_a(request: Request):
        request.state.caller = caller
        request.state.web_user = caller.user
        return caller.user

    async def test_db():
        yield db_session
        await db_session.flush()

    app.dependency_overrides[require_web_user] = signed_in_as_a
    app.dependency_overrides[get_db] = test_db
    yield client, ids_a, ids_b
    app.dependency_overrides.clear()


