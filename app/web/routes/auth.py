from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.repositories.user_repo import UserRepository
from app.web.auth import SESSION_KEY, verify_telegram_login
from app.web.rendering import redirect, render

router = APIRouter(tags=["web-auth"])

# These three routes are deliberately unauthenticated — they are how a person
# becomes authenticated. Every other web router carries require_web_user.


@router.get("/login")
async def login_page(request: Request, error: str | None = None):
    return render(
        request,
        "login.html",
        {
            "error": error,
            "widget_ready": settings.login_widget_ready,
            "bot_username": settings.telegram_bot_username,
            "auth_url": f"{settings.public_base_url}/auth/telegram",
        },
    )


@router.get("/auth/telegram")
async def telegram_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Callback target of the Telegram Login Widget.

    Telegram redirects the browser here with the signed user payload in the
    query string. A valid signature proves the Telegram identity; membership
    of bot_users is what actually grants access.
    """
    params = dict(request.query_params)
    user_id = verify_telegram_login(params)

    if user_id is None:
        return redirect("/login?error=Could+not+verify+that+Telegram+login.")

    user = await UserRepository(db).get_by_telegram_id(user_id)
    if user is None or not user.is_active:
        logger.info("web_login_denied", user_id=user_id, known=user is not None)
        return redirect("/login?error=That+account+does+not+have+access+to+this+bot.")

    request.session[SESSION_KEY] = user_id
    logger.info("web_login_ok", user_id=user_id)
    return redirect("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect("/login")
