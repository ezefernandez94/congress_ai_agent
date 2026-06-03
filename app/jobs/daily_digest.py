from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.services.digest import digest_service


async def send_daily_digest() -> None:
    logger.info("sending_daily_digest")
    try:
        async with AsyncSessionLocal() as db:
            digest_text = await digest_service.generate_daily_digest(db)

        from telegram import Bot

        bot = Bot(token=settings.telegram_bot_token)
        await bot.send_message(
            chat_id=settings.telegram_allowed_user_id,
            text=digest_text,
            parse_mode="Markdown",
        )
        logger.info("daily_digest_sent")
    except Exception as e:
        logger.error("daily_digest_failed", error=str(e))
