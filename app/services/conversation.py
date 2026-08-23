"""Conversation history, shared by the Telegram handlers and the web chat.

Both surfaces key history on the Telegram user ID, so a conversation started
in one continues in the other.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, session_scope
from app.models.conversation import ConversationMessage


async def load_history(user_id: str, limit: int = 20, db: AsyncSession | None = None) -> list[dict]:
    """The last `limit` messages, oldest first, in Anthropic message shape."""

    async def _query(session: AsyncSession) -> list[ConversationMessage]:
        result = await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    if db is not None:
        messages = await _query(db)
    else:
        async with AsyncSessionLocal() as session:
            messages = await _query(session)

    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def save_message(
    user_id: str,
    role: str,
    content: str,
    db: AsyncSession | None = None,
) -> None:
    """Append one turn. Pass `db` to join the caller's transaction."""
    if db is not None:
        db.add(ConversationMessage(user_id=user_id, role=role, content=content))
        await db.flush()
        return

    async with session_scope() as session:
        session.add(ConversationMessage(user_id=user_id, role=role, content=content))
