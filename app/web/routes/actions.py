"""One-click actions that do not fit the generic create/update shape."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.conference_repo import ConferenceRepository
from app.repositories.task_repo import TaskRepository
from app.web.auth import require_web_user
from app.web.rendering import redirect

router = APIRouter(tags=["web-actions"], dependencies=[Depends(require_web_user)])


def _back_to(request: Request, fallback: str) -> str:
    """Return the user to the list they acted from, filters and page intact."""
    referer = request.headers.get("referer") or ""
    # Only trust a same-origin path, never an absolute URL from elsewhere.
    if referer.startswith(str(request.base_url)):
        return "/" + referer[len(str(request.base_url)):]
    return fallback


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    repo = TaskRepository(db)
    task = await repo.get(task_id)
    if task is None:
        return redirect(f"/tasks?error={quote('Task not found')}")

    await repo.complete(task)
    return redirect(_back_to(request, "/tasks"))


@router.post("/conferences/{conference_id}/activate")
async def activate_conference(
    conference_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Make this the conference the agent's system prompt describes."""
    conference = await ConferenceRepository(db).set_active(conference_id)
    if conference is None:
        return redirect(f"/conferences?error={quote('Conference not found')}")
    return redirect(f"/conferences?ok={quote(conference.name + ' is now active')}")
