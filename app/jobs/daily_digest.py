from app.core.config import settings
from app.core.database import session_scope
from app.core.logging import logger
from app.core.scoping import scope_session
from app.repositories.user_repo import UserRepository
from app.services.digest import digest_service


async def _build_digests() -> list[tuple[str, list[int]]]:
    """One digest per workspace, each built on a session scoped to that workspace (REQ-024).

    Returns (digest text, recipient Telegram IDs) pairs, so no session stays open while the
    Telegram sends run.
    """
    async with session_scope() as db:
        by_workspace = await UserRepository(db).digest_recipients_by_workspace()
        chats = {
            workspace_id: [u.telegram_user_id for u in users]
            for workspace_id, users in by_workspace.items()
        }

    digests = []
    for workspace_id, chat_ids in chats.items():
        async with session_scope() as db:
            scope_session(db, workspace_id)
            digests.append((await digest_service.generate_daily_digest(db), chat_ids))
    return digests


async def send_daily_digest() -> None:
    logger.info("sending_daily_digest")
    try:
        digests = await _build_digests()
        if not digests:
            logger.info("daily_digest_no_recipients")
            return

        from telegram import Bot

        bot = Bot(token=settings.telegram_bot_token)
        sent = recipients = 0
        for digest_text, chat_ids in digests:
            for chat_id in chat_ids:
                recipients += 1
                try:
                    await bot.send_message(chat_id=chat_id, text=digest_text, parse_mode="Markdown")
                    sent += 1
                except Exception as e:  # noqa: BLE001 - one blocked chat must not cost others theirs
                    logger.error("daily_digest_send_failed", user_id=chat_id, error=str(e))
        logger.info("daily_digest_sent", sent=sent, recipients=recipients, workspaces=len(digests))
    except Exception as e:  # noqa: BLE001 - a scheduler job that raises is only logged by APScheduler
        logger.error("daily_digest_failed", error=str(e))
