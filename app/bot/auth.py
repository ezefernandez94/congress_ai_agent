from telegram import Update

from app.core.config import settings
from app.core.database import session_scope
from app.core.logging import logger
from app.core.tenancy import Caller, resolve_caller
from app.models.base import WorkspaceRole
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import WorkspaceRepository


async def seed_users_from_env() -> None:
    """Create the bot_users rows for TELEGRAM_ALLOWED_USER_IDS on startup.

    Only ever adds — an ID removed from the env is left untouched in the
    table, so revoking access is done with /removeuser, not by editing .env.
    An owner with no workspace yet joins the Default one as admin, so a fresh
    env ID can sign in; EZE-52 turns env IDs into platform admins instead.
    """
    env_ids = settings.allowed_user_ids
    if not env_ids:
        logger.warning("no_seed_users_configured")
        return

    try:
        async with session_scope() as db:
            repo = UserRepository(db)
            workspaces = WorkspaceRepository(db)
            for user_id in sorted(env_ids):
                user = await repo.ensure_user(user_id, is_owner=True)
                if await workspaces.get_membership(user.id) is None:
                    default = await workspaces.get_or_create_default()
                    await workspaces.add_member(default.id, user.id, WorkspaceRole.admin)
        logger.info("seed_users_ready", count=len(env_ids))
    except Exception as e:  # noqa: BLE001 - startup must survive a seeding failure
        logger.error("seed_users_failed", error=str(e))


async def authorize(update: Update) -> Caller | None:
    """Resolve the sender to a Caller, or None if they may not use the bot.

    Access is an active bot_users row plus a workspace membership, decided in
    resolve_caller. Nobody is ever created here: users get in by being seeded
    from TELEGRAM_ALLOWED_USER_IDS at startup, or by an owner adding them with
    /adduser.
    """
    tg_user = update.effective_user
    if tg_user is None:
        return None

    try:
        async with session_scope() as db:
            caller = await resolve_caller(db, tg_user.id)
    except Exception as e:  # noqa: BLE001 - any failure denies access
        # Fail closed — a database problem must not become an open door.
        logger.error("authorize_db_failed", user_id=tg_user.id, error=str(e))
        return None

    if caller is None:
        logger.info("unauthorized_message", user_id=tg_user.id)
        return None

    return caller
