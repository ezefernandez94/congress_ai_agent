import json
from datetime import date, datetime, timezone

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context_builder import build_system_prompt
from app.agent.tools import TOOLS
from app.core.config import settings
from app.core.logging import logger


class ToolExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, tool_name: str, tool_input: dict) -> dict:
        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if handler is None:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
            return await handler(tool_input)
        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return {"success": False, "error": str(e)}

    async def _tool_create_contact(self, inp: dict) -> dict:
        from app.repositories.company_repo import CompanyRepository
        from app.repositories.person_repo import PersonRepository

        person_repo = PersonRepository(self.db)
        company_id = None

        if inp.get("company_name"):
            company_repo = CompanyRepository(self.db)
            company, _ = await company_repo.get_or_create(inp["company_name"])
            company_id = company.id

        person_data = {
            "full_name": inp["full_name"],
            "role": inp.get("role"),
            "company_id": company_id,
            "linkedin_url": inp.get("linkedin_url"),
            "email": inp.get("email"),
            "contact_type": inp.get("contact_type", "other"),
            "interest_level": inp.get("interest_level", "unknown"),
            "how_met": inp.get("how_met"),
            "notes": inp.get("notes"),
        }
        person = await person_repo.create(person_data)
        return {
            "success": True,
            "person_id": person.id,
            "full_name": person.full_name,
            "company_name": inp.get("company_name"),
        }

    async def _tool_log_interaction(self, inp: dict) -> dict:
        from app.repositories.interaction_repo import InteractionRepository
        from app.repositories.person_repo import PersonRepository
        from sqlalchemy import select
        from app.models.person import Person

        person_repo = PersonRepository(self.db)
        matches = await person_repo.search_by_name(inp["person_name"], limit=5)
        if not matches:
            return {"success": False, "error": f"No contact found matching '{inp['person_name']}'"}
        if len(matches) > 1:
            return {
                "success": False,
                "error": "Multiple contacts found",
                "matches": [{"id": p.id, "name": p.full_name} for p in matches],
            }

        person = matches[0]
        interaction_repo = InteractionRepository(self.db)
        interaction = await interaction_repo.create({
            "person_id": person.id,
            "interaction_type": inp.get("interaction_type", "conversation"),
            "raw_note": inp["summary"],
            "processed_summary": inp["summary"],
            "topics_discussed": inp.get("topics_discussed"),
            "commitments_made": inp.get("commitments_made"),
            "sentiment": inp.get("sentiment"),
            "occurred_at": datetime.now(timezone.utc),
        })

        # Update person's last interaction date
        await person_repo.update(person, {"last_interaction_date": datetime.now(timezone.utc)})
        if not person.first_interaction_date:
            await person_repo.update(person, {"first_interaction_date": datetime.now(timezone.utc)})

        return {"success": True, "interaction_id": interaction.id, "person_name": person.full_name}

    async def _tool_create_task(self, inp: dict) -> dict:
        from app.repositories.person_repo import PersonRepository
        from app.repositories.task_repo import TaskRepository

        task_repo = TaskRepository(self.db)
        person_id = None

        if inp.get("person_name"):
            person_repo = PersonRepository(self.db)
            matches = await person_repo.search_by_name(inp["person_name"], limit=1)
            if matches:
                person_id = matches[0].id

        due_date = None
        if inp.get("due_date"):
            try:
                due_date = date.fromisoformat(inp["due_date"])
            except ValueError:
                pass

        task = await task_repo.create({
            "title": inp["title"],
            "task_type": inp["task_type"],
            "related_person_id": person_id,
            "priority": inp.get("priority", "medium"),
            "due_date": due_date,
            "draft_content": inp.get("draft_content"),
        })
        return {"success": True, "task_id": task.id, "title": task.title}

    async def _tool_search_contacts(self, inp: dict) -> dict:
        from app.services.search import search_service

        contacts = await search_service.search_contacts(
            self.db,
            query=inp["query"],
            contact_type=inp.get("contact_type"),
            limit=inp.get("limit", 5),
        )
        return {
            "success": True,
            "count": len(contacts),
            "contacts": [
                {
                    "id": p.id,
                    "name": p.full_name,
                    "role": p.role,
                    "interest_level": p.interest_level,
                }
                for p in contacts
            ],
        }

    async def _tool_get_contact_brief(self, inp: dict) -> dict:
        from app.repositories.interaction_repo import InteractionRepository
        from app.repositories.person_repo import PersonRepository
        from app.repositories.task_repo import TaskRepository

        person_repo = PersonRepository(self.db)
        matches = await person_repo.search_by_name(inp["person_name"], limit=3)
        if not matches:
            return {"success": False, "error": f"No contact found matching '{inp['person_name']}'"}
        if len(matches) > 1:
            return {
                "success": False,
                "error": "Multiple contacts found",
                "matches": [{"id": p.id, "name": p.full_name} for p in matches],
            }

        person = matches[0]
        interaction_repo = InteractionRepository(self.db)
        interactions = await interaction_repo.get_by_person(person.id, limit=5)
        task_repo = TaskRepository(self.db)
        tasks = await task_repo.get_pending(person_id=person.id)

        return {
            "success": True,
            "person": {
                "id": person.id,
                "name": person.full_name,
                "role": person.role,
                "interest_level": person.interest_level,
                "priority_tier": person.priority_tier,
                "how_met": person.how_met,
                "notes": person.notes,
                "bio_snapshot": person.bio_snapshot,
                "linkedin_summary": person.linkedin_summary,
                "enriched_at": person.enriched_at.isoformat() if person.enriched_at else None,
            },
            "interactions": [
                {"summary": i.processed_summary or i.raw_note, "date": i.occurred_at.isoformat()}
                for i in interactions
            ],
            "open_tasks": [{"id": t.id, "title": t.title, "priority": t.priority} for t in tasks],
        }

    async def _tool_get_pending_tasks(self, inp: dict) -> dict:
        from app.repositories.person_repo import PersonRepository
        from app.repositories.task_repo import TaskRepository

        person_id = None
        if inp.get("person_name"):
            person_repo = PersonRepository(self.db)
            matches = await person_repo.search_by_name(inp["person_name"], limit=1)
            if matches:
                person_id = matches[0].id

        task_repo = TaskRepository(self.db)
        tasks = await task_repo.get_pending(
            priority=inp.get("priority"),
            person_id=person_id,
            limit=inp.get("limit", 10),
        )
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "type": t.task_type,
                }
                for t in tasks
            ],
        }

    async def _tool_complete_task(self, inp: dict) -> dict:
        from app.repositories.task_repo import TaskRepository

        task_repo = TaskRepository(self.db)
        task = None

        if inp.get("task_id"):
            task = await task_repo.get(inp["task_id"])
        elif inp.get("task_title"):
            task = await task_repo.find_by_title(inp["task_title"])

        if not task:
            return {"success": False, "error": "Task not found"}

        await task_repo.complete(task)
        return {"success": True, "task_id": task.id, "title": task.title}

    async def _tool_enrich_contact(self, inp: dict) -> dict:
        from app.repositories.person_repo import PersonRepository
        from app.services.enrichment import enrichment_service

        person_repo = PersonRepository(self.db)
        matches = await person_repo.search_by_name(inp["person_name"], limit=1)
        if not matches:
            return {"success": False, "error": f"No contact found matching '{inp['person_name']}'"}

        person = matches[0]
        updates = {}

        if inp.get("linkedin_url") or person.linkedin_url:
            url = inp.get("linkedin_url") or person.linkedin_url
            try:
                data = await enrichment_service.enrich_person_proxycurl(url)
                updates.update({
                    "linkedin_summary": data.get("summary", ""),
                    "bio_snapshot": data.get("headline", ""),
                    "enriched_at": datetime.now(timezone.utc),
                    "enrichment_source": "proxycurl",
                })
                if inp.get("linkedin_url"):
                    updates["linkedin_url"] = inp["linkedin_url"]
            except Exception as e:
                return {"success": False, "error": f"Enrichment failed: {e}"}

        if updates:
            await person_repo.update(person, updates)

        return {
            "success": True,
            "person_id": person.id,
            "enriched_fields": list(updates.keys()),
        }

    async def _tool_search_web(self, inp: dict) -> dict:
        from app.services.enrichment import enrichment_service

        try:
            results = enrichment_service.tavily.search(
                inp["query"],
                max_results=5,
                days=inp.get("days_back", 90),
            )
            items = results.get("results", [])
            return {
                "success": True,
                "results": [
                    {"title": r.get("title"), "content": r.get("content", "")[:300], "url": r.get("url")}
                    for r in items
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _tool_draft_followup(self, inp: dict) -> dict:
        from app.repositories.person_repo import PersonRepository
        from app.services.followup import followup_service

        person_repo = PersonRepository(self.db)
        matches = await person_repo.search_by_name(inp["person_name"], limit=1)
        if not matches:
            return {"success": False, "error": f"No contact found matching '{inp['person_name']}'"}

        person = matches[0]
        draft = await followup_service.draft_followup_email(
            person_id=person.id,
            db=self.db,
            tone=inp.get("tone", "warm"),
            key_points=inp.get("key_points"),
        )
        return {"success": True, "draft": draft, "person_name": person.full_name}

    async def _tool_generate_meeting_prep(self, inp: dict) -> dict:
        from app.repositories.person_repo import PersonRepository
        from app.services.enrichment import enrichment_service

        person_repo = PersonRepository(self.db)
        matches = await person_repo.search_by_name(inp["person_name"], limit=1)
        if not matches:
            return {"success": False, "error": f"No contact found matching '{inp['person_name']}'"}

        person = matches[0]
        brief = await enrichment_service.generate_intel_brief(person.id, self.db)
        return {"success": True, "brief": brief, "person_name": person.full_name}

    async def _tool_get_daily_digest(self, inp: dict) -> dict:
        from app.services.digest import digest_service

        digest = await digest_service.generate_daily_digest(self.db)
        return {"success": True, "digest": digest}

    async def _tool_get_conference_summary(self, inp: dict) -> dict:
        from sqlalchemy import func, select

        from app.models.interaction import Interaction
        from app.models.opportunity import Opportunity
        from app.models.person import Person
        from app.models.task import Task
        from app.models.base import TaskStatus

        people_count = await self.db.scalar(select(func.count(Person.id)))
        interactions_count = await self.db.scalar(select(func.count(Interaction.id)))
        opportunities_count = await self.db.scalar(select(func.count(Opportunity.id)))
        pending_tasks_count = await self.db.scalar(
            select(func.count(Task.id)).where(Task.status == TaskStatus.pending)
        )

        return {
            "success": True,
            "summary": {
                "total_contacts": people_count,
                "total_interactions": interactions_count,
                "total_opportunities": opportunities_count,
                "pending_tasks": pending_tasks_count,
            },
        }


class ConferenceAgent:
    def __init__(self, db: AsyncSession):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.db = db
        self.tool_executor = ToolExecutor(db)

    async def process_message(
        self,
        user_message: str,
        message_history: list[dict],
        image_b64: str | None = None,
        image_media_type: str = "image/jpeg",
    ) -> str:
        system_prompt = await build_system_prompt(self.db)
        # Build the user message content — text only, or text + image
        if image_b64:
            user_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"{user_message}\n\n"
                        "Extract from this conference badge: full name, company, role/title. "
                        "Then call create_contact with what you find. "
                        "If any field is unclear or not visible, omit it rather than guessing. "
                        "After saving, confirm what was captured and ask if anything should be added."
                    ),
                },
            ]
        else:
            user_content = user_message

        messages = message_history + [{"role": "user", "content": user_content}]

        while True:
            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self.tool_executor.execute(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            break

        return "Sorry, something went wrong. Please try again."

    def _extract_text(self, response) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""
