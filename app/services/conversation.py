"""Conversation history, shared by the Telegram handlers and the web chat.

Both surfaces key history on the Telegram user ID, so a conversation started
in one continues in the other.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationMessage


async def load_history(user_id: str, db: AsyncSession, limit: int = 20) -> list[dict]:
    """The last `limit` messages, oldest first, in Anthropic message shape.

    `db` must be scoped to the caller's workspace (ADR-018); it is required so no caller can read
    history on a session of its own that skipped the scoping.
    """
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def save_message(user_id: str, role: str, content: str, db: AsyncSession) -> None:
    """Append one turn to the caller's transaction, on a workspace-scoped session."""
    db.add(ConversationMessage(user_id=user_id, role=role, content=content))
    await db.flush()
