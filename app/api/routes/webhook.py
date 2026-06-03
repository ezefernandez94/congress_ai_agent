from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.core.logging import logger

router = APIRouter()

_bot_application = None


def set_bot_application(app) -> None:
    global _bot_application
    _bot_application = app


@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    if _bot_application is None:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    from telegram import Update

    update_data = await request.json()
    update = Update.de_json(update_data, _bot_application.bot)
    await _bot_application.process_update(update)

    return {"ok": True}
