"""The web chat runs the agent and keeps history inside the caller's workspace (REQ-024, REQ-018)."""

from sqlalchemy import select

from app.agent.orchestrator import ConferenceAgent
from app.core.scoping import session_workspace
from app.models.conversation import ConversationMessage
from app.services.conversation import save_message


async def test_uc021_chat_history_hides_other_workspace(
    web, db_session, workspace_a, workspace_b, as_workspace
):
    client, _, _ = web
    # Rows can't normally exist for one Telegram ID in two workspaces; if one did, it must stay hidden.
    db = as_workspace(workspace_b)
    await save_message(str(workspace_a.telegram_user_id), "user", "Zebra secret", db=db)
    db_session.info.clear()

    page = await client.get("/chat")

    assert page.status_code == 200
    assert "Zebra secret" not in page.text


async def test_uc021_chat_turn_runs_and_saves_in_own_workspace(
    web, db_session, workspace_a, monkeypatch
):
    client, _, _ = web
    seen_workspace = {}

    async def fake_process(self, message, history, **kwargs):
        seen_workspace["id"] = session_workspace(self.db)
        return "Noted."

    monkeypatch.setattr(ConferenceAgent, "__init__", lambda self, db: setattr(self, "db", db))
    monkeypatch.setattr(ConferenceAgent, "process_message", fake_process)

    response = await client.post("/chat", data={"message": "Met Ann"})

    assert response.status_code == 200
    assert seen_workspace["id"] == workspace_a.id
    saved = (await db_session.execute(select(ConversationMessage))).scalars().all()
    assert {m.workspace_id for m in saved} == {workspace_a.id}
    assert [m.content for m in saved if m.role == "assistant"] == ["Noted."]
