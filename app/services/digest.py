from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import TaskPriority, TaskStatus
from app.models.meeting import Meeting
from app.models.person import Person
from app.models.task import Task


@dataclass
class DigestData:
    """The queried state behind the morning briefing.

    Kept separate from the Telegram formatting so the web dashboard can render
    the same numbers without parsing a Markdown blob back apart.
    """

    day: date
    tasks: list[Task] = field(default_factory=list)
    urgent: list[Task] = field(default_factory=list)
    high: list[Task] = field(default_factory=list)
    other: list[Task] = field(default_factory=list)
    meetings: list[Meeting] = field(default_factory=list)
    priority_contacts: list[Person] = field(default_factory=list)
    overdue: list[Task] = field(default_factory=list)

    @property
    def top_task(self) -> Task | None:
        """The single thing worth doing first."""
        if self.urgent:
            return self.urgent[0]
        if self.high:
            return self.high[0]
        return None


class DigestService:
    async def collect(self, db: AsyncSession, conference_id: str | None = None) -> DigestData:
        today = date.today()
        day_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

        tasks_result = await db.execute(
            select(Task)
            .options(selectinload(Task.person))
            .where(Task.status == TaskStatus.pending)
            .order_by(Task.priority, Task.due_date)
            .limit(20)
        )
        tasks = list(tasks_result.scalars().all())

        meetings_result = await db.execute(
            select(Meeting)
            .options(selectinload(Meeting.participants))
            .where(Meeting.scheduled_at >= day_start, Meeting.scheduled_at <= day_end)
            .order_by(Meeting.scheduled_at)
        )
        meetings = list(meetings_result.scalars().unique().all())

        priority_result = await db.execute(
            select(Person)
            .where(
                Person.priority_tier.in_(["A", "B"]),
                Person.last_interaction_date.is_(None),
            )
            .limit(5)
        )
        priority_contacts = list(priority_result.scalars().all())

        overdue_result = await db.execute(
            select(Task)
            .options(selectinload(Task.person))
            .where(Task.status == TaskStatus.pending, Task.due_date < today)
            .order_by(Task.due_date)
            .limit(5)
        )
        overdue = list(overdue_result.scalars().all())

        return DigestData(
            day=today,
            tasks=tasks,
            urgent=[t for t in tasks if t.priority == TaskPriority.urgent],
            high=[t for t in tasks if t.priority == TaskPriority.high],
            other=[
                t for t in tasks
                if t.priority not in (TaskPriority.urgent, TaskPriority.high)
            ],
            meetings=meetings,
            priority_contacts=priority_contacts,
            overdue=overdue,
        )

    def format_for_telegram(self, data: DigestData) -> str:
        """Render DigestData as the Telegram Markdown the bot has always sent."""
        lines = [
            f"*Good morning! Here's your conference digest for "
            f"{data.day.strftime('%A, %B %d')}*\n"
        ]

        lines.append(f"*Tasks ({len(data.tasks)} pending)*")
        if data.urgent:
            lines.append("⚠️ *Urgent:*")
            for t in data.urgent[:3]:
                due = f" (due {t.due_date})" if t.due_date else ""
                lines.append(f"  • {t.title}{due}")
        if data.high:
            lines.append("🔴 *High:*")
            for t in data.high[:3]:
                due = f" (due {t.due_date})" if t.due_date else ""
                lines.append(f"  • {t.title}{due}")
        if data.other:
            lines.append(f"📋 *Other:* {len(data.other)} more tasks")

        lines.append(f"\n*Today's Meetings ({len(data.meetings)})*")
        if data.meetings:
            for m in data.meetings:
                time_str = m.scheduled_at.strftime("%H:%M") if m.scheduled_at else "TBD"
                lines.append(f"  • {time_str} — {m.title}")
        else:
            lines.append("  No meetings scheduled today.")

        if data.priority_contacts:
            lines.append("\n*Priority Contacts to Approach*")
            for p in data.priority_contacts:
                role_str = f" ({p.role})" if p.role else ""
                lines.append(f"  • {p.full_name}{role_str} — {p.priority_tier.value} tier")

        if data.overdue:
            lines.append(f"\n*⚠️ Overdue Follow-ups ({len(data.overdue)})*")
            for t in data.overdue:
                lines.append(f"  • {t.title} (was due {t.due_date})")

        top = data.top_task
        if top is not None:
            lines.append(f"\n*Most important thing today:* {top.title}")

        return "\n".join(lines)

    async def generate_daily_digest(
        self, db: AsyncSession, conference_id: str | None = None
    ) -> str:
        data = await self.collect(db, conference_id)
        return self.format_for_telegram(data)


digest_service = DigestService()
