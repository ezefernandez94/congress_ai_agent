"""Usage: uv run python scripts/export_crm.py --format csv|airtable|notion"""
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def export_csv(db):
    from sqlalchemy import select

    from app.models.interaction import Interaction
    from app.models.opportunity import Opportunity
    from app.models.person import Person
    from app.models.task import Task

    # People
    result = await db.execute(select(Person))
    people = list(result.scalars().all())
    with open("export_contacts.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "full_name", "role", "email", "linkedin_url",
            "contact_type", "interest_level", "priority_tier",
            "how_met", "notes", "follow_up_status",
        ])
        writer.writeheader()
        for p in people:
            writer.writerow({
                "id": p.id, "full_name": p.full_name, "role": p.role or "",
                "email": p.email or "", "linkedin_url": p.linkedin_url or "",
                "contact_type": p.contact_type, "interest_level": p.interest_level,
                "priority_tier": p.priority_tier, "how_met": p.how_met or "",
                "notes": p.notes or "", "follow_up_status": p.follow_up_status,
            })
    print(f"✅ Exported {len(people)} contacts to export_contacts.csv")

    # Interactions
    result = await db.execute(select(Interaction))
    interactions = list(result.scalars().all())
    with open("export_interactions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "person_id", "interaction_type", "occurred_at", "processed_summary",
        ])
        writer.writeheader()
        for i in interactions:
            writer.writerow({
                "id": i.id, "person_id": i.person_id,
                "interaction_type": i.interaction_type,
                "occurred_at": i.occurred_at.isoformat(),
                "processed_summary": i.processed_summary or "",
            })
    print(f"✅ Exported {len(interactions)} interactions to export_interactions.csv")

    # Tasks
    result = await db.execute(select(Task))
    tasks = list(result.scalars().all())
    with open("export_tasks.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "title", "task_type", "priority", "status", "due_date", "related_person_id",
        ])
        writer.writeheader()
        for t in tasks:
            writer.writerow({
                "id": t.id, "title": t.title, "task_type": t.task_type,
                "priority": t.priority, "status": t.status,
                "due_date": str(t.due_date) if t.due_date else "",
                "related_person_id": t.related_person_id or "",
            })
    print(f"✅ Exported {len(tasks)} tasks to export_tasks.csv")

    # Opportunities
    result = await db.execute(select(Opportunity))
    opportunities = list(result.scalars().all())
    with open("export_opportunities.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "title", "opportunity_type", "stage", "person_id", "estimated_value", "notes",
        ])
        writer.writeheader()
        for o in opportunities:
            writer.writerow({
                "id": o.id, "title": o.title, "opportunity_type": o.opportunity_type,
                "stage": o.stage, "person_id": o.person_id or "",
                "estimated_value": o.estimated_value or "", "notes": o.notes or "",
            })
    print(f"✅ Exported {len(opportunities)} opportunities to export_opportunities.csv")


async def main(fmt: str):
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        if fmt == "csv":
            await export_csv(db)
        elif fmt == "airtable":
            print("Airtable export requires AIRTABLE_API_KEY and BASE_ID in .env — not yet implemented.")
        elif fmt == "notion":
            print("Notion export requires NOTION_API_KEY in .env — not yet implemented.")
        else:
            print(f"Unknown format: {fmt}. Use csv, airtable, or notion.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--format", required=True, choices=["csv", "airtable", "notion"])
    args = parser.parse_args()
    asyncio.run(main(args.format))
