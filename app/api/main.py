import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from telegram.ext import Application

from app.api.middleware import RequestLoggingMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.webhook import router as webhook_router, set_bot_application
from app.bot.router import register_handlers
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.jobs.scheduler import start_scheduler, stop_scheduler

_bot_app: Application | None = None
_polling_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_app, _polling_task
    setup_logging()
    logger.info("starting_up", env=settings.app_env)

    _bot_app = Application.builder().token(settings.telegram_bot_token).build()
    register_handlers(_bot_app)
    await _bot_app.initialize()
    set_bot_application(_bot_app)

    if settings.is_production:
        # Webhook mode — Telegram pushes updates to our public URL
        webhook_url = f"{settings.base_url}/webhook/{settings.webhook_secret}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message", "callback_query"]},
            )
            logger.info("webhook_registered", url=webhook_url, response=resp.json())
    else:
        # Polling mode — bot actively fetches updates from Telegram
        # Must delete any existing webhook first, otherwise polling is ignored
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/deleteWebhook",
                json={"drop_pending_updates": True},
            )
        logger.info("webhook_deleted_polling_mode")

        await _bot_app.start()
        _polling_task = asyncio.create_task(_run_polling(_bot_app))
        logger.info("polling_started")

    await start_scheduler()
    logger.info("startup_complete")

    yield

    logger.info("shutting_down")
    await stop_scheduler()

    if not settings.is_production and _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass

    if _bot_app:
        await _bot_app.stop()
        await _bot_app.shutdown()


async def _run_polling(bot_app: Application) -> None:
    """Continuously poll Telegram for new updates."""
    offset = None
    while True:
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates",
                    json={
                        "offset": offset,
                        "timeout": 30,          # long-poll: waits up to 30s for a message
                        "allowed_updates": ["message", "callback_query"],
                    },
                )
                data = resp.json()

            if not data.get("ok"):
                logger.warning("polling_error", response=data)
                await asyncio.sleep(2)
                continue

            updates = data.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1          # advance cursor
                await bot_app.process_update(
                    bot_app.update_queue._get_update(update)  # noqa: SLF001
                    if hasattr(bot_app.update_queue, "_get_update")
                    else __import__("telegram").Update.de_json(update, bot_app.bot)
                )

        except asyncio.CancelledError:
            logger.info("polling_stopped")
            break
        except Exception as e:
            logger.error("polling_exception", error=str(e))
            await asyncio.sleep(2)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Conference Bot",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health_router)
    app.include_router(webhook_router)
    return app


app = create_app()