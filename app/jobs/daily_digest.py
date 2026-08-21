from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.repositories.user_repo import UserRepository
from app.services.digest import digest_service


async def send_daily_digest() -> None:
    logger.info("sending_daily_digest")
    try:
        async with AsyncSessionLocal() as db:
            recipients = await UserRepository(db).list_digest_recipients()
            if not recipients:
                logger.info("daily_digest_no_recipients")
                return
            digest_text = await digest_service.generate_daily_digest(db)

        from telegram import Bot

        bot = Bot(token=settings.telegram_bot_token)
        sent = 0
        for user in recipients:
            try:
                await bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=digest_text,
                    parse_mode="Markdown",
                )
                sent += 1
            except Exception as e:
                # One blocked chat must not cost everyone else their digest
                logger.error(
                    "daily_digest_send_failed",
                    user_id=user.telegram_user_id,
                    error=str(e),
                )
        logger.info("daily_digest_sent", sent=sent, recipients=len(recipients))
    except Exception as e:
        logger.error("daily_digest_failed", error=str(e))
