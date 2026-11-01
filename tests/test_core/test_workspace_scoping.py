"""The session-level workspace hooks (ADR-018): filtering, stamping, failing closed."""

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import selectinload

from app.core.scoping import CrossWorkspaceWriteError, UnscopedQueryError
from app.models.company import Company
from app.models.conference import Conference
from app.models.interaction import Interaction
from app.models.person import Person
from app.models.user import BotUser
from app.models.workspace import Workspace
from app.repositories.conference_repo import ConferenceRepository
from app.repositories.person_repo import PersonRepository


async def _person(db, name: str, **fields) -> Person:
    return await PersonRepository(db).create({"full_name": name, **fields})


async def test_uc021_select_sees_only_own_workspace(db_session, workspace_a, workspace_b, as_workspace):
    await _person(as_workspace(workspace_b), "Bea From B")
    db = as_workspace(workspace_a)
    await _person(db, "Ann From A")

    names = (await db.execute(select(Person.full_name))).scalars().all()

    assert names == ["Ann From A"]


async def test_uc021_get_by_id_from_other_workspace_is_none(
    db_session, workspace_a, workspace_b, as_workspace
):
    other = await _person(as_workspace(workspace_b), "Bea From B")
    db = as_workspace(workspace_a)

    assert await PersonRepository(db).get(other.id) is None


async def test_uc021_aggregates_and_joins_are_scoped(db_session, workspace_a, workspace_b, as_workspace):
    db_b = as_workspace(workspace_b)
    company_b = Company(name="Shared Name Inc")
    db_b.add(company_b)
    await db_b.flush()
    await _person(db_b, "Bea", company_id=company_b.id)

    db = as_workspace(workspace_a)
    await _person(db, "Ann")

    assert await db.scalar(select(func.count(Person.id))) == 1
    assert await db.scalar(select(func.count()).select_from(Person)) == 1
    joined = await db.execute(select(Person.full_name, Company.name).join(Company))
    assert joined.all() == []


async def test_uc021_relationship_loads_are_scoped(db_session, workspace_a, workspace_b, as_workspace):
    db = as_workspace(workspace_a)
    ann = await _person(db, "Ann")
    # A row from workspace B pointing at A's person can't be made through the app, but the filter must
    # still hide it if one ever exists.
    db.add(Interaction(person_id=ann.id, raw_note="mine"))
    await db.flush()
    db_b = as_workspace(workspace_b)
    db_b.add(Interaction(person_id=ann.id, raw_note="theirs"))
    await db_b.flush()

    db = as_workspace(workspace_a)
    loaded = (
        await db.execute(select(Person).options(selectinload(Person.interactions)))
    ).scalar_one()

    assert [i.raw_note for i in loaded.interactions] == ["mine"]


async def test_uc021_bulk_update_and_delete_are_scoped(
    db_session, workspace_a, workspace_b, as_workspace
):
    await _person(as_workspace(workspace_b), "Bea")
    db = as_workspace(workspace_a)
    await _person(db, "Ann")

    await db.execute(update(Person).values(notes="touched"))
    await db.execute(delete(Person).where(Person.full_name == "Bea"))

    db = as_workspace(workspace_b)
    bea = (await db.execute(select(Person))).scalar_one()
    assert bea.full_name == "Bea"
    assert bea.notes is None


async def test_uc021_set_active_conference_leaves_other_workspace_alone(
    db_session, workspace_a, workspace_b, as_workspace
):
    db_b = as_workspace(workspace_b)
    conf_b = await ConferenceRepository(db_b).create({"name": "B Summit", "is_active": True})
    db = as_workspace(workspace_a)
    conf_a = await ConferenceRepository(db).create({"name": "A Summit", "is_active": False})

    await ConferenceRepository(db).set_active(conf_a.id)

    db_b = as_workspace(workspace_b)
    still_active = await ConferenceRepository(db_b).get_active()
    assert still_active is not None and still_active.id == conf_b.id


async def test_uc021_new_rows_stamped_with_workspace_and_creator(scoped_db, workspace_a):
    person = await _person(scoped_db, "Ann")

    assert person.workspace_id == workspace_a.id
    assert person.created_by_user_id == workspace_a.user_id


async def test_uc021_insert_into_other_workspace_refused(scoped_db, workspace_b):
    scoped_db.add(Person(full_name="Sneaky", workspace_id=workspace_b.id))

    with pytest.raises(CrossWorkspaceWriteError):
        await scoped_db.flush()


async def test_uc021_moving_row_to_other_workspace_refused(scoped_db, workspace_b):
    person = await _person(scoped_db, "Ann")
    person.workspace_id = workspace_b.id

    with pytest.raises(CrossWorkspaceWriteError):
        await scoped_db.flush()


async def test_uc021_unscoped_session_fails_closed(db_session, workspace_a, as_workspace):
    await _person(as_workspace(workspace_a), "Ann")
    db_session.info.clear()

    with pytest.raises(UnscopedQueryError):
        await db_session.execute(select(Person))
    with pytest.raises(UnscopedQueryError):
        await db_session.execute(select(func.count()).select_from(Conference))


async def test_uc021_unscoped_insert_fails_closed(db_session):
    db_session.add(Person(full_name="Nobody's"))

    with pytest.raises(UnscopedQueryError):
        await db_session.flush()


async def test_uc021_unscoped_tables_still_readable_without_workspace(db_session, workspace_a):
    db_session.info.clear()

    assert await db_session.scalar(select(func.count()).select_from(Workspace)) >= 1
    assert await db_session.scalar(select(func.count()).select_from(BotUser)) >= 1


async def test_uc021_same_linkedin_url_allowed_in_two_workspaces(
    db_session, workspace_a, workspace_b, as_workspace
):
    url = "https://www.linkedin.com/in/ada"
    await _person(as_workspace(workspace_a), "Ada", linkedin_url=url)
    await _person(as_workspace(workspace_b), "Ada", linkedin_url=url)
