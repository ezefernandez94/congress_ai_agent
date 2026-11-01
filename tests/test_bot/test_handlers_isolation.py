"""Telegram turns run the agent and keep history inside the sender's workspace (REQ-024, REQ-018)."""

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

import app.bot.auth as bot_auth
from app.agent.orchestrator import ConferenceAgent
from app.bot import handlers
from app.core import tenancy
from app.core.scoping import session_workspace
from app.models.conversation import ConversationMessage


async def test_uc001_text_turn_runs_and_saves_in_senders_workspace(
    db_session, workspace_a, workspace_b, use_test_session, monkeypatch
):
    use_test_session(bot_auth, tenancy)
    seen = {}

    async def fake_process(self, user_message, message_history, **kwargs):
        seen["workspace"] = session_workspace(self.db)
        seen["history"] = message_history
        return "Saved Ann."

    monkeypatch.setattr(ConferenceAgent, "__init__", lambda self, db: setattr(self, "db", db))
    monkeypatch.setattr(ConferenceAgent, "process_message", fake_process)
    update = MagicMock()
    update.effective_user.id = workspace_b.telegram_user_id
    update.message.text = "Met Ann from Acme"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()

    await handlers.handle_text_message(update, context)

    assert seen["workspace"] == workspace_b.id
    saved = (await db_session.execute(select(ConversationMessage))).scalars().all()
    assert {m.workspace_id for m in saved} == {workspace_b.id}
    assert {m.created_by_user_id for m in saved} == {workspace_b.user_id}
    update.message.reply_text.assert_awaited_with("Saved Ann.", parse_mode="Markdown")
