"""Browser authentication for the web UI.

Access is decided by the same `bot_users` table the Telegram bot uses
(`app/bot/auth.py`) — there is no separate web account, no password column and
no second allowlist. A person proves they own a Telegram account via the
Telegram Login Widget, and that account must already be an active bot user.
"""

import hashlib
import hmac
import time
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.tenancy import resolve_caller
from app.models.user import BotUser
from app.repositories.user_repo import UserRepository

SESSION_KEY = "uid"

# Telegram signs the widget payload at login time. Anything older than this is
# a replayed URL rather than a fresh sign-in.
MAX_AUTH_AGE_SECONDS = 24 * 60 * 60


class NotLoggedIn(Exception):
    """Raised by the route dependency; handled app-wide as a redirect to /login."""

    def __init__(self, reason: str = "login_required"):
        self.reason = reason
        super().__init__(reason)


class NotAnOwner(Exception):
    """Raised when a signed-in user lacks the owner flag an admin page requires."""


def verify_telegram_login(params: dict[str, Any]) -> int | None:
    """Validate a Telegram Login Widget payload and return the Telegram user ID.

    Returns None on any failure. The check is the one Telegram documents:
    HMAC-SHA256 over the sorted `key=value` pairs, keyed by SHA256 of the bot
    token — which is why only the holder of the token can mint a valid payload.
    """
    received_hash = params.get("hash")
    if not received_hash or not settings.telegram_bot_token:
        return None

    data_check_string = "\n".join(
        f"{key}={params[key]}" for key in sorted(params) if key != "hash"
    )
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        logger.warning("web_login_bad_signature")
        return None

    try:
        auth_date = int(params.get("auth_date", 0))
        user_id = int(params["id"])
    except (KeyError, TypeError, ValueError):
        logger.warning("web_login_malformed_payload")
        return None

    if time.time() - auth_date > MAX_AUTH_AGE_SECONDS:
        logger.warning("web_login_stale", age_seconds=int(time.time() - auth_date))
        return None

    return user_id


async def require_web_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BotUser:
    """Resolve the browser session to an active BotUser, or raise NotLoggedIn.

    The workspace comes from resolve_caller, the same function the bot uses, and
    is kept on request.state.caller for the routes that need it.

    The user is re-read from the database on every request rather than trusted
    from the cookie, so revoking someone with /removeuser in Telegram also
    locks them out of the web UI immediately.
    """
    # Development bypass. The Telegram Login Widget cannot run against
    # localhost — it only renders on the domain registered with BotFather —
    # so local work signs in as the owner. Gated on is_production, which is
    # driven by APP_ENV, so it cannot fire on Railway.
    if not settings.is_production:
        owner = await UserRepository(db).first_owner()
        caller = await resolve_caller(db, owner.telegram_user_id) if owner else None
        if caller is None:
            raise NotLoggedIn("no_owner_seeded")
        request.state.caller = caller
        request.state.web_user = caller.user
        return caller.user

    user_id = request.session.get(SESSION_KEY)
    if not user_id:
        raise NotLoggedIn()

    try:
        caller = await resolve_caller(db, int(user_id))
    except Exception as e:
        # Fail closed, matching app/bot/auth.py — a database problem must not
        # become an open door.
        logger.error("web_authorize_db_failed", user_id=user_id, error=str(e))
        raise NotLoggedIn("lookup_failed") from e

    if caller is None:
        logger.info("web_unauthorized", user_id=user_id)
        request.session.pop(SESSION_KEY, None)
        raise NotLoggedIn("revoked")

    request.state.caller = caller
    request.state.web_user = caller.user
    return caller.user


async def require_owner(user: BotUser = Depends(require_web_user)) -> BotUser:
    """Extra gate for pages that manage other users."""
    if not user.is_owner:
        raise NotAnOwner()
    return user
