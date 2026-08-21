from telegram import Update

from app.core.config import settings
from app.core.database import session_scope
from app.core.logging import logger
from app.models.user import BotUser
from app.repositories.user_repo import UserRepository


async def seed_users_from_env() -> None:
    """Create the bot_users rows for TELEGRAM_ALLOWED_USER_IDS on startup.

    Only ever adds — an ID removed from the env is left untouched in the
    table, so revoking access is done with /removeuser, not by editing .env.
    """
    env_ids = settings.allowed_user_ids
    if not env_ids:
        logger.warning("no_seed_users_configured")
        return

    try:
        async with session_scope() as db:
            repo = UserRepository(db)
            for user_id in sorted(env_ids):
                await repo.ensure_user(user_id, is_owner=True)
        logger.info("seed_users_ready", count=len(env_ids))
    except Exception as e:
        logger.error("seed_users_failed", error=str(e))


async def authorize(update: Update) -> BotUser | None:
    """Resolve the sender to a BotUser, or None if they may not use the bot.

    The bot_users table is the only source of access. Nobody is ever created
    here: users get in by being seeded from TELEGRAM_ALLOWED_USER_IDS at
    startup, or by an existing user adding them with /adduser.
    """
    tg_user = update.effective_user
    if tg_user is None:
        return None

    try:
        async with session_scope() as db:
            user = await UserRepository(db).get_by_telegram_id(tg_user.id)
    except Exception as e:
        # Fail closed — a database problem must not become an open door.
        logger.error("authorize_db_failed", user_id=tg_user.id, error=str(e))
        return None

    if user is None or not user.is_active:
        logger.info("unauthorized_message", user_id=tg_user.id, known=user is not None)
        return None

    return user
