import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from telegram.ext import Application

from app.api.middleware import RequestLoggingMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.webhook import router as webhook_router, set_bot_application
from app.bot.auth import seed_users_from_env
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

    await seed_users_from_env()

    _bot_app = Application.builder().token(settings.telegram_bot_token).build()
    register_handlers(_bot_app)
    await _bot_app.initialize()
    set_bot_application(_bot_app)

    # Log which bot this token actually drives. Development mode deletes the
    # token's webhook, so starting up against a production token would take the
    # production bot offline — this makes the mistake visible immediately.
    me = await _bot_app.bot.get_me()
    logger.info(
        "bot_identity",
        username=me.username,
        bot_id=me.id,
        mode="webhook" if settings.is_production else "polling",
    )

    if settings.is_production:
        # Webhook mode — Telegram pushes updates to our public URL
        await _register_webhook()
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
        if _bot_app.running:
            await _bot_app.stop()
        await _bot_app.shutdown()


def _redact(url: str) -> str:
    """Webhook URLs embed the secret and API URLs embed the bot token."""
    return url.replace(settings.webhook_secret, "***").replace(settings.telegram_bot_token, "***")


async def _register_webhook() -> None:
    """Point Telegram at this deployment, refusing to start if it doesn't take.

    A rejected setWebhook used to be logged as a success, leaving a container
    that passed health checks while the bot silently received nothing. Crashing
    here surfaces the misconfiguration in the deploy instead.
    """
    webhook_url = settings.webhook_url
    api = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{api}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["message", "callback_query"]},
        )
        body = resp.json()

        if resp.status_code != 200 or not body.get("ok"):
            logger.error(
                "webhook_registration_failed",
                url=_redact(webhook_url),
                status=resp.status_code,
                description=body.get("description"),
            )
            raise RuntimeError(
                f"Telegram rejected setWebhook for {_redact(webhook_url)}: "
                f"{body.get('description', resp.text)}"
            )

        logger.info("webhook_registered", url=_redact(webhook_url))

        # setWebhook only validates the URL's syntax — it never checks that the
        # host is reachable. Surface whatever Telegram saw on its last delivery
        # so an unreachable domain shows up here and not as a silent dead bot.
        info = (await client.get(f"{api}/getWebhookInfo")).json().get("result", {})
        if info.get("last_error_message"):
            logger.warning(
                "webhook_last_delivery_error",
                message=info["last_error_message"],
                pending=info.get("pending_update_count", 0),
                hint="Stale if it predates this deploy; persistent means Telegram cannot reach BASE_URL.",
            )
        else:
            logger.info("webhook_healthy", pending=info.get("pending_update_count", 0))


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