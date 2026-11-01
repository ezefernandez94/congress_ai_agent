"""Every agent tool, run from workspace A, must never see or touch workspace B (REQ-024, ADR-018).

The agent picks tools and arguments itself, so each tool gets a leak case, not just the repositories.
search_web reads no stored data and has none.
"""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.agent.context_builder import build_system_prompt
from app.agent.orchestrator import ToolExecutor
from app.models.base import TaskStatus
from app.models.company import Company
from app.models.conference import Conference
from app.models.interaction import Interaction
from app.models.meeting import Meeting
from app.models.opportunity import Opportunity
from app.models.person import Person
from app.models.task import Task

SECRET = "Bea Secret"
LINKEDIN = "https://www.linkedin.com/in/bea-secret"


@pytest.fixture
async def other_workspace_data(db_session, workspace_a, workspace_b, as_workspace):
    """A full set of workspace B records, then a session switched to workspace A."""
    db = as_workspace(workspace_b)
    company = Company(name="Globex")
    db.add(company)
    db.add(Conference(name="B Summit", is_active=True, goals=["B goal"]))
    await db.flush()
    bea = Person(full_name=SECRET, company_id=company.id, linkedin_url=LINKEDIN, notes="robotics")
    db.add(bea)
    await db.flush()
    db.add(Interaction(person_id=bea.id, raw_note="B private talk"))
    task = Task(title="Send Bea the deck", related_person_id=bea.id, due_date=date.today())
    db.add(task)
    db.add(Opportunity(title="B deal", opportunity_type="investment", person_id=bea.id))
    db.add(Meeting(title="B meeting", scheduled_at=None))
    await db.flush()
    ids = {"person": bea.id, "task": task.id, "company": company.id}

    as_workspace(workspace_a)
    return ids


@pytest.fixture
def tools(db_session, other_workspace_data) -> ToolExecutor:
    executor = ToolExecutor(db_session)
    # The executor commits or rolls back per tool; in a test either would end the shared transaction
    # that holds both workspaces' rows.
    db_session.commit = AsyncMock()
    db_session.rollback = AsyncMock()
    return executor


async def test_uc021_search_contacts_cannot_see_other_workspace(tools):
    result = await tools.execute("search_contacts", {"query": "bea"})
    assert result["success"] is True
    assert SECRET not in str(result)

    result = await tools.execute("search_contacts", {"query": "robotics"})
    assert SECRET not in str(result)


async def test_uc021_get_contact_brief_cannot_see_other_workspace(tools):
    result = await tools.execute("get_contact_brief", {"person_name": "Bea"})
    assert result["success"] is False
    assert "B private talk" not in str(result)


async def test_uc021_log_interaction_cannot_reach_other_workspace(tools, db_session):
    result = await tools.execute("log_interaction", {"person_name": "Bea", "summary": "hi"})
    assert result["success"] is False


async def test_uc021_create_task_does_not_link_other_workspace_person(tools, db_session):
    result = await tools.execute(
        "create_task", {"title": "Ping Bea", "task_type": "follow_up", "person_name": "Bea"}
    )
    assert result["success"] is True
    task = await db_session.scalar(select(Task).where(Task.id == result["task_id"]))
    assert task.related_person_id is None


async def test_uc021_get_pending_tasks_cannot_see_other_workspace(tools):
    result = await tools.execute("get_pending_tasks", {})
    assert "Send Bea the deck" not in str(result)

    result = await tools.execute("get_pending_tasks", {"person_name": "Bea"})
    assert "Send Bea the deck" not in str(result)


async def test_uc021_complete_task_cannot_touch_other_workspace(
    tools, db_session, other_workspace_data, workspace_b, as_workspace
):
    by_id = await tools.execute("complete_task", {"task_id": other_workspace_data["task"]})
    by_title = await tools.execute("complete_task", {"task_title": "Send Bea"})
    assert by_id["success"] is False
    assert by_title["success"] is False

    db = as_workspace(workspace_b)
    task = await db.scalar(select(Task).where(Task.id == other_workspace_data["task"]))
    assert task.status == TaskStatus.pending


async def test_uc021_enrich_contact_cannot_reach_other_workspace(tools, monkeypatch):
    from app.services.enrichment import enrichment_service

    proxycurl = AsyncMock(return_value={})
    monkeypatch.setattr(enrichment_service, "enrich_person_proxycurl", proxycurl)

    result = await tools.execute("enrich_contact", {"person_name": "Bea"})

    assert result["success"] is False
    proxycurl.assert_not_awaited()


async def test_uc021_draft_followup_cannot_reach_other_workspace(tools, monkeypatch):
    from app.services.followup import followup_service

    draft = AsyncMock(return_value="draft")
    monkeypatch.setattr(followup_service, "draft_followup_email", draft)

    result = await tools.execute("draft_followup", {"person_name": "Bea"})

    assert result["success"] is False
    draft.assert_not_awaited()


async def test_uc021_generate_meeting_prep_cannot_reach_other_workspace(tools, monkeypatch):
    from app.services.enrichment import enrichment_service

    brief = AsyncMock(return_value="brief")
    monkeypatch.setattr(enrichment_service, "generate_intel_brief", brief)

    result = await tools.execute("generate_meeting_prep", {"person_name": "Bea"})

    assert result["success"] is False
    brief.assert_not_awaited()


async def test_uc021_create_contact_stays_in_own_workspace(tools, db_session, workspace_a):
    result = await tools.execute(
        "create_contact",
        {"full_name": "Ann Mine", "company_name": "Globex", "linkedin_url": LINKEDIN},
    )

    assert result["success"] is True
    person = await db_session.scalar(select(Person).where(Person.full_name == "Ann Mine"))
    company = await db_session.scalar(select(Company).where(Company.id == person.company_id))
    # Same company name as workspace B's, but A gets its own row.
    assert company.workspace_id == workspace_a.id
    assert person.workspace_id == workspace_a.id
    assert person.created_by_user_id == workspace_a.user_id


async def test_uc021_get_daily_digest_cannot_see_other_workspace(tools):
    result = await tools.execute("get_daily_digest", {})
    assert result["success"] is True
    assert "Send Bea the deck" not in result["digest"]
    assert SECRET not in result["digest"]


async def test_uc021_get_conference_summary_counts_only_own_workspace(tools):
    result = await tools.execute("get_conference_summary", {})
    assert result["summary"] == {
        "total_contacts": 0,
        "total_interactions": 0,
        "total_opportunities": 0,
        "pending_tasks": 0,
    }


async def test_uc021_system_prompt_cannot_see_other_workspace(db_session, other_workspace_data):
    prompt = await build_system_prompt(db_session)
    assert "B Summit" not in prompt
    assert SECRET not in prompt
    assert "No active conference configured." in prompt
