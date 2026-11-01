"""Usage: uv run python scripts/batch_enrich.py --input attendees.csv"""
import asyncio
import csv
import sys
from datetime import UTC
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def enrich_row(row: dict, db) -> dict:
    from app.repositories.company_repo import CompanyRepository
    from app.repositories.person_repo import PersonRepository
    from app.services.enrichment import enrichment_service

    person_repo = PersonRepository(db)
    company_id = None

    if row.get("company"):
        company_repo = CompanyRepository(db)
        company, _ = await company_repo.get_or_create(row["company"])
        company_id = company.id

    # Check if person already exists
    existing = None
    if row.get("linkedin_url"):
        existing = await person_repo.get_by_linkedin_url(row["linkedin_url"])
    if not existing:
        matches = await person_repo.search_by_name(row["full_name"], limit=1)
        if matches:
            existing = matches[0]

    if not existing:
        person = await person_repo.create({
            "full_name": row["full_name"],
            "company_id": company_id,
            "linkedin_url": row.get("linkedin_url") or None,
            "contact_type": row.get("contact_type", "other"),
        })
    else:
        person = existing

    if person.linkedin_url and not person.enriched_at:
        try:
            data = await enrichment_service.enrich_person_proxycurl(person.linkedin_url)
            from datetime import datetime
            await person_repo.update(person, {
                "linkedin_summary": data.get("summary", ""),
                "bio_snapshot": data.get("headline", ""),
                "enriched_at": datetime.now(UTC),
                "enrichment_source": "proxycurl",
            })
            return {"name": person.full_name, "status": "enriched"}
        except Exception as e:  # noqa: BLE001 - one bad row is reported, the rest still run
            return {"name": person.full_name, "status": f"error: {e}"}

    return {"name": person.full_name, "status": "skipped (no LinkedIn or already enriched)"}


async def main(input_file: str, workspace: str | None):
    from app.core.database import session_scope
    from app.core.tenancy import find_workspace, workspace_session

    # Fail on a bad --workspace before reading the CSV or calling any paid API.
    async with session_scope() as db:
        workspace = (await find_workspace(db, workspace)).id

    rows = []
    with open(input_file, newline="") as f:  # noqa: ASYNC230 - one-shot CLI, nothing else runs on the loop
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Processing {len(rows)} contacts...\n")
    results = []

    for i, row in enumerate(rows):
        async with workspace_session(workspace) as db:
            result = await enrich_row(row, db)

        results.append(result)
        print(f"[{i+1}/{len(rows)}] {result['name']}: {result['status']}")
        await asyncio.sleep(1)  # rate limit: 1 req/sec

    # Summary
    enriched = sum(1 for r in results if r["status"] == "enriched")
    errors = sum(1 for r in results if r["status"].startswith("error"))
    print(f"\n✅ Done. Enriched: {enriched}, Skipped: {len(results) - enriched - errors}, Errors: {errors}")

    with open("enriched_contacts_summary.txt", "w") as f:  # noqa: ASYNC230 - one-shot CLI, nothing else runs on the loop
        f.writelines(f"{r['name']}: {r['status']}\n" for r in results)
    print("Summary written to enriched_contacts_summary.txt")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV file with full_name, company, linkedin_url, contact_type")
    parser.add_argument("--workspace", help="Workspace name or id; optional when there is only one")
    args = parser.parse_args()

    from app.core.tenancy import WorkspaceChoiceError

    try:
        asyncio.run(main(args.input, args.workspace))
    except WorkspaceChoiceError as e:
        sys.exit(str(e))
