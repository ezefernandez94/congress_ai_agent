from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import WorkspaceRole
from app.models.user import BotUser
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
