from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import SYSTEM_IDENTITY
from app.models.conference import Conference
from app.models.meeting import Meeting
from app.models.person import Person
from app.models.task import Task
from app.models.base import TaskStatus


async def get_active_conference(db: AsyncSession) -> Conference | None:
    result = await db.execute(select(Conference).where(Conference.is_active == True).limit(1))  # noqa: E712
    return result.scalar_one_or_none()


async def get_pending_tasks_summary(db: AsyncSession, limit: int = 5) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.status == TaskStatus.pending)
        .order_by(Task.priority)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_todays_meetings(db: AsyncSession) -> list[Meeting]:
    from datetime import datetime, timezone

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=timezone.utc)
    result = await db.execute(
        select(Meeting)
        .where(Meeting.scheduled_at >= today_start, Meeting.scheduled_at <= today_end)
        .order_by(Meeting.scheduled_at)
    )
    return list(result.scalars().all())


async def get_recent_contacts(db: AsyncSession, hours: int = 24) -> list[Person]:
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(Person)
        .where(Person.created_at >= cutoff)
        .order_by(Person.created_at.desc())
        .limit(10)
    )
    return list(result.scalars().all())


def format_recent_contacts(contacts: list[Person]) -> str:
    if not contacts:
        return "No new contacts in the last 24 hours."
    lines = []
    for p in contacts:
        role_str = f", {p.role}" if p.role else ""
        lines.append(f"  • {p.full_name}{role_str}")
    return "\n".join(lines)


async def build_system_prompt(db: AsyncSession) -> str:
    conference = await get_active_conference(db)
    pending_tasks = await get_pending_tasks_summary(db, limit=5)
    todays_meetings = await get_todays_meetings(db)
    recent_contacts = await get_recent_contacts(db, hours=24)

    if conference:
        conf_section = (
            f"## Conference Context\n"
            f"Name: {conference.name}\n"
            f"Location: {conference.location or 'TBD'}\n"
            f"Dates: {conference.start_date} to {conference.end_date}\n"
        )
        if conference.goals:
            conf_section += "Goals:\n" + "\n".join(f"- {g}" for g in conference.goals)
    else:
        conf_section = "## Conference Context\nNo active conference configured."

    state_section = (
        f"## Current State\n"
        f"Today's date: {date.today().isoformat()}\n"
        f"Pending tasks: {len(pending_tasks)} shown (may be more)\n"
        f"Today's meetings: {len(todays_meetings)} scheduled\n"
    )

    recent_section = (
        f"## Recent Activity (last 24h)\n"
        f"{format_recent_contacts(recent_contacts)}"
    )

    return f"{SYSTEM_IDENTITY}\n\n{conf_section}\n\n{state_section}\n\n{recent_section}"
