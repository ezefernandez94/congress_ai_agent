"""Browser front end for the same agent the Telegram bot talks to."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import ConferenceAgent
from app.core.database import get_db
from app.core.logging import logger
from app.models.user import BotUser
from app.services.conversation import load_history, save_message
from app.web.auth import require_web_user
from app.web.rendering import render

router = APIRouter(prefix="/chat", tags=["web-chat"])

HISTORY_LIMIT = 20


@router.get("")
async def chat_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: BotUser = Depends(require_web_user),
):
    history = await load_history(str(user.telegram_user_id), limit=HISTORY_LIMIT, db=db)
    return render(request, "chat/index.html", {"history": history, "user": user})


@router.post("")
async def send(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: BotUser = Depends(require_web_user),
):
    """Run one agent turn and swap the whole log back in via HTMX."""
    form = await request.form()
    message = (form.get("message") or "").strip()
    user_key = str(user.telegram_user_id)

    if not message:
        history = await load_history(user_key, limit=HISTORY_LIMIT, db=db)
        return render(request, "chat/_log.html", {"history": history, "user": user})

    history = await load_history(user_key, limit=HISTORY_LIMIT, db=db)

    try:
        reply = await ConferenceAgent(db).process_message(message, history)
    except Exception as e:
        logger.error("web_chat_failed", user_id=user_key, error=str(e))
        reply = "Something went wrong talking to the agent. Please try again."
    else:
        # Only persist a turn the agent actually completed, so a failed call
        # does not poison the history the next request replays.
        await save_message(user_key, "user", message, db=db)
        await save_message(user_key, "assistant", reply, db=db)

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return render(request, "chat/_log.html", {"history": history, "user": user})
