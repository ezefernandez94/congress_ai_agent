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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_app
    setup_logging()
    logger.info("starting_up", env=settings.app_env)

    _bot_app = Application.builder().token(settings.telegram_bot_token).build()
    register_handlers(_bot_app)
    await _bot_app.initialize()
    set_bot_application(_bot_app)

    if settings.is_production:
        webhook_url = f"{settings.base_url}/webhook/{settings.webhook_secret}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
                json={"url": webhook_url},
            )
            logger.info("webhook_registered", url=webhook_url, response=resp.json())

    await start_scheduler()
    logger.info("startup_complete")

    yield

    logger.info("shutting_down")
    await stop_scheduler()
    if _bot_app:
        await _bot_app.shutdown()


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
