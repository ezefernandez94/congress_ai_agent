import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.interaction import Interaction
from app.models.person import Person
from app.models.task import Task


class FollowUpService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def draft_followup_email(
        self,
        person_id: str,
        db: AsyncSession,
        tone: str = "warm",
        key_points: list[str] | None = None,
    ) -> str:
        result = await db.execute(select(Person).where(Person.id == person_id))
        person = result.scalar_one_or_none()
        if not person:
            return "Person not found."

        interactions_result = await db.execute(
            select(Interaction)
            .where(Interaction.person_id == person_id)
            .order_by(Interaction.occurred_at.desc())
            .limit(3)
        )
        interactions = list(interactions_result.scalars().all())

        tasks_result = await db.execute(
            select(Task).where(Task.related_person_id == person_id).limit(5)
        )
        tasks = list(tasks_result.scalars().all())

        context_parts = [
            f"Contact: {person.full_name}",
            f"Role: {person.role or 'Unknown'}",
            f"How we met: {person.how_met or 'Unknown'}",
            f"Notes: {person.notes or 'None'}",
        ]
        if interactions:
            summaries = [i.processed_summary or i.raw_note or "" for i in interactions if i.processed_summary or i.raw_note]
            if summaries:
                context_parts.append(f"Conversation highlights: {'; '.join(summaries[:2])}")
        if tasks:
            pending = [t.title for t in tasks if t.status == "pending"]
            if pending:
                context_parts.append(f"Pending actions: {', '.join(pending)}")

        context = "\n".join(context_parts)
        points_str = "\n".join(f"- {p}" for p in (key_points or []))

        message = await self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": (
                    f"Write a {tone} follow-up email from me to {person.full_name}.\n"
                    f"Context:\n{context}\n"
                    + (f"Key points to include:\n{points_str}\n" if points_str else "")
                    + "Length: 4-6 sentences. No generic openers like 'Hope this finds you well'. "
                    "Reference a specific detail from our conversation. Start directly with the message body."
                ),
            }],
        )

        return message.content[0].text


followup_service = FollowUpService()
