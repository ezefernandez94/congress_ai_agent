"""Usage: uv run python scripts/seed_conference.py [--workspace <name or id>]"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.tenancy import WorkspaceChoiceError, workspace_session
from app.models.conference import Conference


async def main(workspace: str | None):
    print("=== Conference Seed ===\n")

    name = input("Conference name: ").strip()
    location = input("Location: ").strip()
    start_date = input("Start date (YYYY-MM-DD): ").strip()
    end_date = input("End date (YYYY-MM-DD): ").strip()

    print("Enter goals (one per line, empty line to finish):")
    goals = []
    while True:
        line = input("  Goal: ").strip()
        if not line:
            break
        goals.append(line)

    print("Target contact types (comma-separated, e.g. investor,customer,founder):")
    types_raw = input("  Types: ").strip()
    target_types = [t.strip() for t in types_raw.split(",") if t.strip()]

    from datetime import date

    async with workspace_session(workspace) as db:
        # Deactivate the workspace's active conference (the session limits this to the workspace)
        from sqlalchemy import update
        await db.execute(
            update(Conference).where(Conference.is_active == True).values(is_active=False)
        )

        conference = Conference(
            name=name,
            location=location or None,
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            goals=goals or None,
            target_contact_types=target_types or None,
            is_active=True,
        )
        db.add(conference)
        await db.flush()

    print(f"\n✅ Conference '{name}' created with ID: {conference.id}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", help="Workspace name or id; optional when there is only one")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.workspace))
    except WorkspaceChoiceError as e:
        sys.exit(str(e))
