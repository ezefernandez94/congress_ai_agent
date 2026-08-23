"""CrudConfig for each entity. The route bodies live in app/web/crud.py."""

from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from starlette.datastructures import FormData, QueryParams

from app.models.company import Company
from app.models.conference import Conference
from app.models.interaction import Interaction
from app.models.meeting import Meeting
from app.models.note import Note
from app.models.opportunity import Opportunity
from app.models.person import Person
from app.models.task import Task
from app.models.base import TaskStatus
from app.repositories.company_repo import CompanyRepository
from app.repositories.conference_repo import ConferenceRepository
from app.repositories.interaction_repo import InteractionRepository
from app.repositories.meeting_repo import MeetingRepository
from app.repositories.note_repo import NoteRepository
from app.repositories.opportunity_repo import OpportunityRepository
from app.repositories.person_repo import PersonRepository
from app.repositories.task_repo import TaskRepository
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.conference import ConferenceCreate, ConferenceUpdate
from app.schemas.interaction import InteractionCreate, InteractionUpdate
from app.schemas.meeting import MeetingCreate, MeetingUpdate
from app.schemas.note import NoteCreate, NoteUpdate
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate
from app.schemas.person import PersonCreate, PersonUpdate
from app.schemas.task import TaskCreate, TaskUpdate
from app.web.crud import CrudConfig, build_router


# --- dropdown data shared by several forms ---------------------------------


async def _people_options(db: AsyncSession) -> list[Person]:
    result = await db.execute(select(Person).order_by(Person.full_name).limit(1000))
    return list(result.scalars().all())


async def _company_options(db: AsyncSession) -> list[Company]:
    result = await db.execute(select(Company).order_by(Company.name).limit(1000))
    return list(result.scalars().all())


async def _meeting_options(db: AsyncSession) -> list[Meeting]:
    result = await db.execute(
        select(Meeting).order_by(Meeting.scheduled_at.desc().nullslast()).limit(500)
    )
    return list(result.scalars().all())


async def _conference_options(db: AsyncSession) -> list[Conference]:
    return await ConferenceRepository(db).list_all()


async def people_and_companies(db: AsyncSession) -> dict[str, Any]:
    return {"people": await _people_options(db), "companies": await _company_options(db)}


# --- filters that are not a plain column equality --------------------------


def _date_range(column: Any, params: QueryParams, prefix: str = "") -> list[ColumnElement[bool]]:
    """`?from=YYYY-MM-DD&to=YYYY-MM-DD` over a date or datetime column."""
    where: list[ColumnElement[bool]] = []
    is_datetime = isinstance(column.type.python_type, type) and column.type.python_type is datetime

    for key, op in ((f"{prefix}from", "ge"), (f"{prefix}to", "le")):
        raw = (params.get(key) or "").strip()
        if not raw:
            continue
        try:
            parsed: Any = date.fromisoformat(raw)
        except ValueError:
            continue
        if is_datetime:
            edge = time.min if op == "ge" else time.max
            parsed = datetime.combine(parsed, edge, tzinfo=timezone.utc)
        where.append(column >= parsed if op == "ge" else column <= parsed)

    return where


def _task_extra(params: QueryParams) -> list[ColumnElement[bool]]:
    where: list[ColumnElement[bool]] = _date_range(Task.due_date, params, "due_")
    if params.get("overdue"):
        where.append(Task.due_date < date.today())
        where.append(Task.status == TaskStatus.pending)
    return where


def _person_extra(params: QueryParams) -> list[ColumnElement[bool]]:
    where: list[ColumnElement[bool]] = []
    if params.get("never_contacted"):
        where.append(Person.last_interaction_date.is_(None))
    return where


def _interaction_extra(params: QueryParams) -> list[ColumnElement[bool]]:
    return _date_range(Interaction.occurred_at, params)


def _meeting_extra(params: QueryParams) -> list[ColumnElement[bool]]:
    where: list[ColumnElement[bool]] = _date_range(Meeting.scheduled_at, params)
    followed = params.get("followed_up")
    if followed in ("yes", "no"):
        where.append(Meeting.followed_up.is_(followed == "yes"))
    return where


# --- detail-page context ---------------------------------------------------


async def _person_detail(db: AsyncSession, person: Person) -> dict[str, Any]:
    return {"companies": await _company_options(db)}


async def _company_detail(db: AsyncSession, company: Company) -> dict[str, Any]:
    return {}


# --- save hooks ------------------------------------------------------------


async def _save_meeting_participants(db: AsyncSession, meeting: Meeting, form: FormData) -> None:
    """participant_ids is a schema field but not a column — it drives the M2M."""
    await MeetingRepository(db).set_participants(
        meeting, [pid for pid in form.getlist("participant_ids") if pid]
    )


async def _enforce_single_active(db: AsyncSession, conference: Conference, form: FormData) -> None:
    """Exactly one conference may be active; the agent reads whichever one is."""
    if form.get("is_active") is not None:
        await ConferenceRepository(db).set_active(conference.id)


# --- configurations --------------------------------------------------------

PEOPLE = CrudConfig(
    slug="people",
    title="People",
    singular="Contact",
    model=Person,
    repo=PersonRepository,
    create_schema=PersonCreate,
    update_schema=PersonUpdate,
    form_fields=[
        "full_name", "role", "company_id", "linkedin_url", "email", "phone",
        "twitter_handle", "contact_type", "priority_tier", "interest_level",
        "warmth_score", "how_met", "notes", "follow_up_status", "next_action",
        "next_action_due", "linkedin_summary", "bio_snapshot",
    ],
    filter_columns={
        "contact_type": Person.contact_type,
        "priority_tier": Person.priority_tier,
        "interest_level": Person.interest_level,
        "follow_up_status": Person.follow_up_status,
        "company_id": Person.company_id,
    },
    search_columns=[Person.full_name, Person.notes, Person.bio_snapshot, Person.role],
    extra_where=_person_extra,
    order_by=[Person.full_name],
    list_options=[selectinload(Person.company)],
    detail_options=[
        selectinload(Person.company),
        selectinload(Person.interactions),
        selectinload(Person.tasks),
        selectinload(Person.opportunities),
        selectinload(Person.meetings),
        selectinload(Person.note_records),
    ],
    form_context=lambda db: people_and_companies(db),
    detail_context=_person_detail,
    delete_warning="Their interaction history is deleted too. ",
)

COMPANIES = CrudConfig(
    slug="companies",
    title="Companies",
    singular="Company",
    model=Company,
    repo=CompanyRepository,
    create_schema=CompanyCreate,
    update_schema=CompanyUpdate,
    form_fields=[
        "name", "website", "linkedin_url", "crunchbase_url", "industry", "stage",
        "funding_total", "last_funding_date", "strategic_notes", "company_summary",
    ],
    form_arrays=["investor_list", "relevance_tags"],
    filter_columns={"industry": Company.industry, "stage": Company.stage},
    search_columns=[Company.name, Company.industry, Company.company_summary, Company.strategic_notes],
    order_by=[Company.name],
    list_options=[selectinload(Company.people)],
    detail_options=[selectinload(Company.people), selectinload(Company.opportunities)],
    detail_context=_company_detail,
)

TASKS = CrudConfig(
    slug="tasks",
    title="Tasks",
    singular="Task",
    model=Task,
    repo=TaskRepository,
    create_schema=TaskCreate,
    update_schema=TaskUpdate,
    form_fields=[
        "title", "description", "task_type", "related_person_id", "related_company_id",
        "related_meeting_id", "priority", "status", "due_date", "created_by", "draft_content",
    ],
    filter_columns={
        "status": Task.status,
        "priority": Task.priority,
        "task_type": Task.task_type,
        "related_person_id": Task.related_person_id,
    },
    search_columns=[Task.title, Task.description],
    extra_where=_task_extra,
    order_by=[Task.status, Task.priority, Task.due_date.asc().nullslast()],
    list_options=[selectinload(Task.person)],
    detail_options=[selectinload(Task.person)],
    form_defaults={"created_by": "user"},
    form_context=lambda db: people_and_companies(db),
)

OPPORTUNITIES = CrudConfig(
    slug="opportunities",
    title="Opportunities",
    singular="Opportunity",
    model=Opportunity,
    repo=OpportunityRepository,
    create_schema=OpportunityCreate,
    update_schema=OpportunityUpdate,
    form_fields=[
        "title", "opportunity_type", "person_id", "company_id", "stage",
        "estimated_value", "probability", "expected_close_date", "notes",
        "next_step", "next_step_due",
    ],
    form_arrays=["pitch_feedback", "objections_raised"],
    filter_columns={
        "stage": Opportunity.stage,
        "opportunity_type": Opportunity.opportunity_type,
        "person_id": Opportunity.person_id,
        "company_id": Opportunity.company_id,
    },
    search_columns=[Opportunity.title, Opportunity.notes, Opportunity.next_step],
    order_by=[Opportunity.stage, Opportunity.expected_close_date.asc().nullslast()],
    list_options=[selectinload(Opportunity.person), selectinload(Opportunity.company)],
    detail_options=[selectinload(Opportunity.person), selectinload(Opportunity.company)],
    form_context=lambda db: people_and_companies(db),
)

INTERACTIONS = CrudConfig(
    slug="interactions",
    title="Interactions",
    singular="Interaction",
    model=Interaction,
    repo=InteractionRepository,
    create_schema=InteractionCreate,
    update_schema=InteractionUpdate,
    form_fields=[
        "person_id", "meeting_id", "interaction_type", "occurred_at", "raw_note",
        "processed_summary", "sentiment", "source", "transcription",
    ],
    form_arrays=["topics_discussed"],
    filter_columns={
        "person_id": Interaction.person_id,
        "interaction_type": Interaction.interaction_type,
        "sentiment": Interaction.sentiment,
        "source": Interaction.source,
    },
    search_columns=[Interaction.raw_note, Interaction.processed_summary, Interaction.transcription],
    extra_where=_interaction_extra,
    order_by=[Interaction.occurred_at.desc()],
    list_options=[selectinload(Interaction.person)],
    detail_options=[selectinload(Interaction.person), selectinload(Interaction.meeting)],
    form_context=lambda db: _interaction_form_context(db),
)

MEETINGS = CrudConfig(
    slug="meetings",
    title="Meetings",
    singular="Meeting",
    model=Meeting,
    repo=MeetingRepository,
    create_schema=MeetingCreate,
    update_schema=MeetingUpdate,
    form_fields=[
        "title", "scheduled_at", "duration_minutes", "location", "meeting_type",
        "conference_id", "prep_brief", "outcome_summary", "sentiment", "followed_up_at",
    ],
    form_arrays=["talking_points", "questions_to_ask", "next_steps"],
    form_booleans=["followed_up"],
    form_multi=["participant_ids"],
    dump_exclude=["participant_ids"],
    value_overrides={"participant_ids": lambda m: [p.id for p in m.participants]},
    filter_columns={"meeting_type": Meeting.meeting_type, "conference_id": Meeting.conference_id},
    search_columns=[Meeting.title, Meeting.location, Meeting.outcome_summary, Meeting.prep_brief],
    extra_where=_meeting_extra,
    order_by=[Meeting.scheduled_at.desc().nullslast()],
    list_options=[selectinload(Meeting.participants)],
    detail_options=[
        selectinload(Meeting.participants),
        selectinload(Meeting.interactions),
        selectinload(Meeting.notes),
    ],
    form_context=lambda db: _meeting_form_context(db),
    on_save=_save_meeting_participants,
)

NOTES = CrudConfig(
    slug="notes",
    title="Notes",
    singular="Note",
    model=Note,
    repo=NoteRepository,
    create_schema=NoteCreate,
    update_schema=NoteUpdate,
    form_fields=["person_id", "meeting_id", "raw_content", "content_type", "transcription"],
    form_booleans=["processed"],
    filter_columns={
        "content_type": Note.content_type,
        "person_id": Note.person_id,
    },
    search_columns=[Note.raw_content, Note.transcription],
    extra_where=lambda params: (
        [Note.processed.is_(params.get("processed") == "yes")]
        if params.get("processed") in ("yes", "no")
        else []
    ),
    order_by=[Note.created_at.desc()],
    list_options=[selectinload(Note.person)],
    detail_options=[selectinload(Note.person), selectinload(Note.meeting)],
    form_context=lambda db: _note_form_context(db),
)

CONFERENCES = CrudConfig(
    slug="conferences",
    title="Conferences",
    singular="Conference",
    model=Conference,
    repo=ConferenceRepository,
    create_schema=ConferenceCreate,
    update_schema=ConferenceUpdate,
    form_fields=["name", "location", "start_date", "end_date", "post_conference_report"],
    form_arrays=["goals", "target_contact_types"],
    form_booleans=["is_active", "schedule_imported", "summary_generated"],
    filter_columns={},
    search_columns=[Conference.name, Conference.location],
    order_by=[Conference.start_date.desc().nullslast()],
    on_save=_enforce_single_active,
)


async def _interaction_form_context(db: AsyncSession) -> dict[str, Any]:
    return {"people": await _people_options(db), "meetings": await _meeting_options(db)}


async def _meeting_form_context(db: AsyncSession) -> dict[str, Any]:
    return {"people": await _people_options(db), "conferences": await _conference_options(db)}


async def _note_form_context(db: AsyncSession) -> dict[str, Any]:
    return {"people": await _people_options(db), "meetings": await _meeting_options(db)}


CONFIGS = [PEOPLE, COMPANIES, TASKS, OPPORTUNITIES, INTERACTIONS, MEETINGS, NOTES, CONFERENCES]

entity_routers = [build_router(c) for c in CONFIGS]
