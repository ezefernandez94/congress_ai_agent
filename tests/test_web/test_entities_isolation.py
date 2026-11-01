"""Every web route, signed in to workspace A, must never show or change workspace B (REQ-024).

The routes run for real over HTTP with the real get_scoped_db; only the sign-in is replaced by the
caller from workspace A, and get_db yields the test's session.
"""

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.conference import Conference
from app.models.interaction import Interaction
from app.models.meeting import Meeting
from app.models.note import Note
from app.models.opportunity import Opportunity
from app.models.person import Person
from app.models.task import Task
from tests.test_web.conftest import MARK_B

# slug -> (model, form for a valid update)
ENTITIES = {
    "people": (Person, {"full_name": "Changed"}),
    "companies": (Company, {"name": "Changed"}),
    "tasks": (Task, {"title": "Changed", "task_type": "other", "priority": "medium",
                     "status": "pending"}),
    "opportunities": (Opportunity, {"title": "Changed", "opportunity_type": "investment",
                                    "stage": "identified"}),
    "interactions": (Interaction, {"raw_note": "Changed"}),
    "meetings": (Meeting, {"title": "Changed", "meeting_type": "spontaneous"}),
    "notes": (Note, {"raw_content": "Changed", "content_type": "text"}),
    "conferences": (Conference, {"name": "Changed"}),
}


@pytest.mark.parametrize("slug", ENTITIES)
async def test_uc021_list_and_export_show_only_own_workspace(web, slug):
    client, _, _ = web

    page = await client.get(f"/{slug}")
    export = await client.get(f"/{slug}/export.csv")

    assert page.status_code == 200
    assert MARK_B not in page.text
    assert MARK_B not in export.text
    assert export.text.count("\n") == 2  # header + workspace A's one row


@pytest.mark.parametrize("slug", ENTITIES)
async def test_uc021_other_workspace_record_not_found(web, slug):
    client, _, ids_b = web
    other = ids_b[slug]

    edit = await client.get(f"/{slug}/{other}/edit")
    assert edit.status_code == 303
    assert "not+found" in edit.headers["location"] or "not%20found" in edit.headers["location"]
    if slug != "notes" and slug != "interactions":
        detail = await client.get(f"/{slug}/{other}")
        assert MARK_B not in detail.text


@pytest.mark.parametrize("slug", ENTITIES)
async def test_uc021_other_workspace_record_cannot_be_changed_or_deleted(
    web, slug, db_session, workspace_b, as_workspace
):
    client, _, ids_b = web
    model, form = ENTITIES[slug]
    other = ids_b[slug]

    await client.post(f"/{slug}/{other}", data=form)
    await client.post(f"/{slug}/{other}/delete")

    db = as_workspace(workspace_b)
    row = await db.scalar(select(model).where(model.id == other))
    assert row is not None
    assert "Changed" not in str([getattr(row, f) for f in form if hasattr(row, f)])


@pytest.mark.parametrize(
    ("slug", "form", "field"),
    [
        ("people", {"full_name": "New", "company_id": "companies"}, "company_id"),
        ("tasks", {"title": "New", "task_type": "other", "priority": "medium", "status": "pending",
                   "related_person_id": "people"}, "related_person_id"),
        ("interactions", {"raw_note": "New", "person_id": "people"}, "person_id"),
        ("opportunities", {"title": "New", "opportunity_type": "investment", "stage": "identified",
                           "company_id": "companies"}, "company_id"),
        ("meetings", {"title": "New", "meeting_type": "spontaneous",
                      "conference_id": "conferences"}, "conference_id"),
        ("notes", {"raw_content": "New", "content_type": "text", "person_id": "people"},
         "person_id"),
    ],
)
async def test_uc021_form_cannot_link_other_workspace_record(web, slug, form, field):
    client, _, ids_b = web
    form = {**form, field: ids_b[form[field]]}

    response = await client.post(f"/{slug}", data=form)

    assert response.status_code == 422
    assert field in response.text


async def test_uc021_meeting_participants_from_other_workspace_dropped(web, db_session):
    client, ids_a, ids_b = web

    await client.post(
        f"/meetings/{ids_a['meetings']}",
        data={"title": "Mine", "meeting_type": "spontaneous",
              "participant_ids": [ids_a["people"], ids_b["people"]]},
    )

    from app.repositories.meeting_repo import MeetingRepository

    meeting = await MeetingRepository(db_session).get_with_participants(ids_a["meetings"])
    assert [p.id for p in meeting.participants] == [ids_a["people"]]


async def test_uc021_dashboard_counts_only_own_workspace(web):
    client, _, _ = web

    page = await client.get("/")

    assert page.status_code == 200
    assert MARK_B not in page.text


async def test_uc021_actions_cannot_touch_other_workspace(web, db_session, workspace_b, as_workspace):
    client, _, ids_b = web

    done = await client.post(f"/tasks/{ids_b['tasks']}/complete")
    activate = await client.post(f"/conferences/{ids_b['conferences']}/activate")

    assert "not+found" in done.headers["location"] or "not%20found" in done.headers["location"]
    assert "not" in activate.headers["location"]
    db = as_workspace(workspace_b)
    task = await db.scalar(select(Task).where(Task.id == ids_b["tasks"]))
    conference = await db.scalar(select(Conference).where(Conference.id == ids_b["conferences"]))
    assert task.status == "pending"
    assert conference.is_active is not True
