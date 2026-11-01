from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import session_scope
from app.core.scoping import scope_session
from app.models.base import WorkspaceRole
from app.models.user import BotUser
from app.models.workspace import Workspace
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import WorkspaceRepository


@dataclass(frozen=True)
class Caller:
    """Who is acting and in which workspace."""

    user: BotUser
    workspace_id: str
    role: WorkspaceRole


async def resolve_caller(db: AsyncSession, telegram_user_id: int) -> Caller | None:
    """Map a Telegram user to their workspace, or None if they may not use the product.

    This is the only place that decides a caller's workspace (ADR-014): the bot's
    authorize and the web's require_web_user both call it, so a dedicated deployment
    or a new way of choosing the workspace changes one function. Database errors
    propagate; the callers turn them into a denial.
    """
    user = await UserRepository(db).get_by_telegram_id(telegram_user_id)
    if user is None or not user.is_active:
        return None

    membership = await WorkspaceRepository(db).get_membership(user.id)
    if membership is None:
        # Access without a workspace would leave every later query unscoped, so it's a denial.
        return None

    return Caller(user=user, workspace_id=membership.workspace_id, role=membership.role)


def scope_to_caller(db: AsyncSession, caller: Caller) -> AsyncSession:
    """Limit a session to the caller's workspace and record them as the creator of new rows."""
    scope_session(db, caller.workspace_id, caller.user.id)
    return db


@asynccontextmanager
async def caller_session(caller: Caller) -> AsyncGenerator[AsyncSession, None]:
    """session_scope() bound to the caller's workspace: the way bot handlers open a session."""
    async with session_scope() as db:
        yield scope_to_caller(db, caller)


class WorkspaceChoiceError(ValueError):
    """A script's --workspace did not name exactly one workspace."""


async def find_workspace(db: AsyncSession, choice: str | None) -> Workspace:
    """Resolve a script's --workspace (id or exact name) to one workspace.

    Leaving it out is allowed only when there is exactly one workspace, so a script on a shared
    deployment can never pick an organization by accident.
    """
    workspaces = await WorkspaceRepository(db).list_all()
    if choice is None:
        if len(workspaces) == 1:
            return workspaces[0]
        raise WorkspaceChoiceError(
            "Pass --workspace <name or id>. Workspaces: " + _describe(workspaces)
            if workspaces
            else "There are no workspaces yet."
        )

    matches = [w for w in workspaces if choice in (w.id, w.name)]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise WorkspaceChoiceError(f"Several workspaces are named '{choice}'; pass the id: "
                                   + _describe(matches))
    raise WorkspaceChoiceError(f"No workspace '{choice}'. Workspaces: " + _describe(workspaces))


def _describe(workspaces: list[Workspace]) -> str:
    return ", ".join(f"{w.name} ({w.id})" for w in workspaces) or "none"


@asynccontextmanager
async def workspace_session(choice: str | None) -> AsyncGenerator[AsyncSession, None]:
    """session_scope() for a script, bound to the workspace its --workspace names.

    Scripts run as an operator, not as a bot user, so the rows they create have no creator.
    """
    async with session_scope() as db:
        workspace = await find_workspace(db, choice)
        scope_session(db, workspace.id)
        yield db
