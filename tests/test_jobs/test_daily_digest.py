"""The morning digest is built per workspace and sent only to that workspace's users (REQ-011, REQ-024)."""

from unittest.mock import AsyncMock, MagicMock

import telegram

import app.jobs.daily_digest as job
from app.models.task import Task
from app.repositories.user_repo import UserRepository


async def test_uc010_each_user_gets_own_workspace_digest(
    db_session, workspace_a, workspace_b, as_workspace, use_test_session, monkeypatch
):
    db = as_workspace(workspace_a)
    db.add(Task(title="Antelope follow-up", priority="high"))
    await db.flush()
    db = as_workspace(workspace_b)
    db.add(Task(title="Zebra follow-up", priority="high"))
    await db.flush()
    db_session.info.clear()
    use_test_session(job)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    monkeypatch.setattr(telegram, "Bot", MagicMock(return_value=bot))

    await job.send_daily_digest()

    sent = {c.kwargs["chat_id"]: c.kwargs["text"] for c in bot.send_message.await_args_list}
    assert "Antelope follow-up" in sent[workspace_a.telegram_user_id]
    assert "Zebra" not in sent[workspace_a.telegram_user_id]
    assert "Zebra follow-up" in sent[workspace_b.telegram_user_id]
    assert "Antelope" not in sent[workspace_b.telegram_user_id]


async def test_uc010_user_without_workspace_gets_no_digest(db_session):
    await UserRepository(db_session).ensure_user(900_099)

    grouped = await UserRepository(db_session).digest_recipients_by_workspace()

    assert all(
        u.telegram_user_id != 900_099 for users in grouped.values() for u in users
    )
