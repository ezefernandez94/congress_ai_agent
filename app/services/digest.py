from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import TaskPriority, TaskStatus
from app.models.conference import Conference
from app.models.meeting import Meeting
from app.models.person import Person
from app.models.task import Task


class DigestService:
    async def generate_daily_digest(self, db: AsyncSession, conference_id: str | None = None) -> str:
        today = date.today()

        # Pending tasks
        tasks_result = await db.execute(
            select(Task)
            .where(Task.status == TaskStatus.pending)
            .order_by(Task.priority, Task.due_date)
            .limit(20)
        )
        tasks = list(tasks_result.scalars().all())

        # Today's meetings
        meetings_result = await db.execute(
            select(Meeting)
            .where(
                Meeting.scheduled_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc),
                Meeting.scheduled_at < datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc),
            )
            .order_by(Meeting.scheduled_at)
        )
        meetings = list(meetings_result.scalars().all())

        # High-priority contacts not yet followed up
        priority_contacts_result = await db.execute(
            select(Person)
            .where(
                Person.priority_tier.in_(["A", "B"]),
                Person.last_interaction_date.is_(None),
            )
            .limit(5)
        )
        priority_contacts = list(priority_contacts_result.scalars().all())

        lines = [f"*Good morning! Here's your conference digest for {today.strftime('%A, %B %d')}*\n"]

        # Tasks section
        urgent = [t for t in tasks if t.priority == TaskPriority.urgent]
        high = [t for t in tasks if t.priority == TaskPriority.high]
        other = [t for t in tasks if t.priority not in (TaskPriority.urgent, TaskPriority.high)]

        lines.append(f"*Tasks ({len(tasks)} pending)*")
        if urgent:
            lines.append("⚠️ *Urgent:*")
            for t in urgent[:3]:
                due = f" (due {t.due_date})" if t.due_date else ""
                lines.append(f"  • {t.title}{due}")
        if high:
            lines.append("🔴 *High:*")
            for t in high[:3]:
                due = f" (due {t.due_date})" if t.due_date else ""
                lines.append(f"  • {t.title}{due}")
        if other:
            lines.append(f"📋 *Other:* {len(other)} more tasks")

        # Meetings section
        lines.append(f"\n*Today's Meetings ({len(meetings)})*")
        if meetings:
            for m in meetings:
                time_str = m.scheduled_at.strftime("%H:%M") if m.scheduled_at else "TBD"
                lines.append(f"  • {time_str} — {m.title}")
        else:
            lines.append("  No meetings scheduled today.")

        # Priority contacts
        if priority_contacts:
            lines.append(f"\n*Priority Contacts to Approach*")
            for p in priority_contacts:
                role_str = f" ({p.role})" if p.role else ""
                lines.append(f"  • {p.full_name}{role_str} — {p.priority_tier} tier")

        # Overdue follow-ups
        overdue_result = await db.execute(
            select(Task)
            .where(
                Task.status == TaskStatus.pending,
                Task.due_date < today,
            )
            .limit(5)
        )
        overdue = list(overdue_result.scalars().all())
        if overdue:
            lines.append(f"\n*⚠️ Overdue Follow-ups ({len(overdue)})*")
            for t in overdue:
                lines.append(f"  • {t.title} (was due {t.due_date})")

        # Most important action
        if urgent:
            lines.append(f"\n*Most important thing today:* {urgent[0].title}")
        elif high:
            lines.append(f"\n*Most important thing today:* {high[0].title}")

        return "\n".join(lines)


digest_service = DigestService()
