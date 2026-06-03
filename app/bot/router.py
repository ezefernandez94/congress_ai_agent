from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.handlers import handle_text_message, handle_voice_message
from app.core.config import settings
from app.core.database import AsyncSessionLocal


async def start_command(update: Update, context) -> None:
    if update.effective_user.id != settings.telegram_allowed_user_id:
        return
    await update.message.reply_text(
        "👋 *Conference Assistant ready.*\n\n"
        "Tell me about people you meet, ask for briefs, or request follow-up drafts.\n\n"
        "Commands:\n"
        "/digest — Morning briefing\n"
        "/tasks — Pending tasks\n"
        "/contacts — Recent contacts\n"
        "/help — This message",
        parse_mode="Markdown",
    )


async def digest_command(update: Update, context) -> None:
    if update.effective_user.id != settings.telegram_allowed_user_id:
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    from app.services.digest import digest_service

    async with AsyncSessionLocal() as db:
        digest = await digest_service.generate_daily_digest(db)
    await update.message.reply_text(digest, parse_mode="Markdown")


async def tasks_command(update: Update, context) -> None:
    if update.effective_user.id != settings.telegram_allowed_user_id:
        return
    from app.bot.formatter import format_task_list
    from app.repositories.task_repo import TaskRepository

    async with AsyncSessionLocal() as db:
        task_repo = TaskRepository(db)
        tasks = await task_repo.get_pending(limit=10)
        task_dicts = [
            {"title": t.title, "priority": t.priority, "due_date": str(t.due_date) if t.due_date else None}
            for t in tasks
        ]

    await update.message.reply_text(format_task_list(task_dicts), parse_mode="Markdown")


async def contacts_command(update: Update, context) -> None:
    if update.effective_user.id != settings.telegram_allowed_user_id:
        return
    from app.repositories.person_repo import PersonRepository

    async with AsyncSessionLocal() as db:
        person_repo = PersonRepository(db)
        contacts = await person_repo.get_recent(hours=72, limit=10)

    if not contacts:
        await update.message.reply_text("No contacts added in the last 3 days.")
        return

    lines = ["*Recent contacts:*"]
    for p in contacts:
        role_str = f" — {p.role}" if p.role else ""
        lines.append(f"• {p.full_name}{role_str}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def help_command(update: Update, context) -> None:
    await start_command(update, context)


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("digest", digest_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("contacts", contacts_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
