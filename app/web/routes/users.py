"""Manage who may use the bot — the web mirror of /adduser and /removeuser."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.user import BotUser
from app.repositories.user_repo import UserRepository
from app.web.auth import require_owner
from app.web.rendering import redirect, render

router = APIRouter(prefix="/users", tags=["web-users"])


@router.get("")
async def index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: BotUser = Depends(require_owner),
):
    return render(request, "users/list.html", {"rows": await UserRepository(db).list_all()})


@router.post("")
async def add(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: BotUser = Depends(require_owner),
):
    form = await request.form()
    raw_id = (form.get("telegram_user_id") or "").strip()
    display_name = (form.get("display_name") or "").strip() or None

    try:
        telegram_user_id = int(raw_id)
    except ValueError:
        return redirect(f"/users?error={quote('Telegram user ID must be a number')}")

    await UserRepository(db).ensure_user(telegram_user_id, display_name=display_name)
    logger.info("web_user_added", by=user.telegram_user_id, user_id=telegram_user_id)
    return redirect(f"/users?ok={quote('User added')}")


@router.post("/{telegram_user_id}/active")
async def set_active(
    telegram_user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: BotUser = Depends(require_owner),
):
    # Locking yourself out of the tool you are using is never the intent.
    if telegram_user_id == user.telegram_user_id:
        return redirect(f"/users?error={quote('You cannot deactivate your own account')}")

    form = await request.form()
    active = form.get("active") == "1"
    updated = await UserRepository(db).set_active(telegram_user_id, active)
    if updated is None:
        return redirect(f"/users?error={quote('User not found')}")

    logger.info("web_user_active_changed", by=user.telegram_user_id, user_id=telegram_user_id, active=active)
    return redirect(f"/users?ok={quote('Access ' + ('restored' if active else 'revoked'))}")


@router.post("/{telegram_user_id}/digest")
async def set_digest(
    telegram_user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: BotUser = Depends(require_owner),
):
    form = await request.form()
    enabled = form.get("enabled") == "1"
    updated = await UserRepository(db).set_digest_preference(telegram_user_id, enabled)
    if updated is None:
        return redirect(f"/users?error={quote('User not found')}")
    return redirect(f"/users?ok={quote('Digest preference updated')}")
