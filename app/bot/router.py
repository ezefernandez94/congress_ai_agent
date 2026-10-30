from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.auth import authorize
from app.bot.handlers import handle_photo_message, handle_text_message, handle_voice_message
from app.core.database import AsyncSessionLocal, session_scope
from app.repositories.user_repo import UserRepository
from app.repositories.workspace_repo import WorkspaceRepository


async def start_command(update: Update, context) -> None:
    if await authorize(update) is None:
        return
    await update.message.reply_text(
        "👋 *Conference Assistant ready.*\n\n"
        "Tell me about people you meet, ask for briefs, or request follow-up drafts.\n\n"
        "Commands:\n"
        "/digest — Morning briefing\n"
        "/tasks — Pending tasks\n"
        "/contacts — Recent contacts\n"
        "/digest\\_on, /digest\\_off — Toggle your morning digest\n"
        "/users — Who can use this bot\n"
        "/adduser `<telegram id>` — Give someone access\n"
        "/removeuser `<telegram id>` — Revoke access\n"
        "/whoami — Your Telegram ID\n"
        "/help — This message",
        parse_mode="Markdown",
    )


async def digest_command(update: Update, context) -> None:
    if await authorize(update) is None:
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    from app.services.digest import digest_service

    async with AsyncSessionLocal() as db:
        digest = await digest_service.generate_daily_digest(db)
    await update.message.reply_text(digest, parse_mode="Markdown")


async def tasks_command(update: Update, context) -> None:
    if await authorize(update) is None:
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
    if await authorize(update) is None:
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


async def whoami_command(update: Update, context) -> None:
    """Unauthenticated on purpose — this is how a new person finds the ID to
    send to an existing user so they can be added."""
    user = update.effective_user
    await update.message.reply_text(
        f"Your Telegram ID is `{user.id}`.\n"
        "Send it to someone who already uses this bot and ask them to run "
        "/adduser with it.",
        parse_mode="Markdown",
    )


async def digest_on_command(update: Update, context) -> None:
    await _set_own_digest(update, True)


async def digest_off_command(update: Update, context) -> None:
    await _set_own_digest(update, False)


async def _set_own_digest(update: Update, enabled: bool) -> None:
    caller = await authorize(update)
    if caller is None:
        return
    async with session_scope() as db:
        await UserRepository(db).set_digest_preference(caller.user.telegram_user_id, enabled)
    await update.message.reply_text(
        "✅ You'll get the morning digest." if enabled else "🔕 Morning digest turned off."
    )


async def users_command(update: Update, context) -> None:
    if await authorize(update) is None:
        return
    async with AsyncSessionLocal() as db:
        users = await UserRepository(db).list_all()

    lines = ["*Bot users:*"]
    for u in users:
        name = u.display_name or "(unnamed)"
        flags = []
        if u.is_owner:
            flags.append("owner")
        if not u.is_active:
            flags.append("revoked")
        if u.receives_digest:
            flags.append("digest")
        lines.append(f"• {name} — `{u.telegram_user_id}` ({', '.join(flags) or 'no digest'})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def adduser_command(update: Update, context) -> None:
    caller = await authorize(update)
    if caller is None:
        return
    if not caller.user.is_owner:
        await update.message.reply_text("Only an owner can add users.")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: `/adduser <telegram id> [name]`\n"
            "The new person can get their ID by sending /whoami to this bot.",
            parse_mode="Markdown",
        )
        return

    try:
        new_id = int(args[0])
    except ValueError:
        await update.message.reply_text(f"`{args[0]}` is not a valid Telegram ID.", parse_mode="Markdown")
        return

    display_name = " ".join(args[1:]) or None

    async with session_scope() as db:
        repo = UserRepository(db)
        workspaces = WorkspaceRepository(db)
        existing = await repo.get_by_telegram_id(new_id)
        membership = await workspaces.get_membership(existing.id) if existing else None
        if membership and membership.workspace_id != caller.workspace_id:
            # A user belongs to exactly one workspace (REQ-024); moving people between
            # organizations is not something an owner of one of them can do.
            await update.message.reply_text("That user belongs to another workspace.")
            return
        if existing and existing.is_active and membership:
            await update.message.reply_text("That user already has access.")
            return
        if existing:
            await repo.set_active(new_id, True)          # re-enable a revoked user
            user = existing
        else:
            user = await repo.ensure_user(new_id, display_name=display_name)
        if membership is None:
            await workspaces.add_member(caller.workspace_id, user.id)

    await update.message.reply_text(
        f"✅ `{new_id}` can now use the bot. They should send /start.", parse_mode="Markdown"
    )


async def removeuser_command(update: Update, context) -> None:
    caller = await authorize(update)
    if caller is None:
        return
    if not caller.user.is_owner:
        await update.message.reply_text("Only an owner can remove users.")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: `/removeuser <telegram id>`", parse_mode="Markdown")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text(f"`{args[0]}` is not a valid Telegram ID.", parse_mode="Markdown")
        return

    if target_id == caller.user.telegram_user_id:
        await update.message.reply_text("You can't revoke your own access.")
        return

    async with session_scope() as db:
        repo = UserRepository(db)
        target = await repo.get_by_telegram_id(target_id)
        if target is None:
            await update.message.reply_text("No such user.")
            return
        if target.is_owner:
            await update.message.reply_text(
                "That user is an owner. Remove their ID from TELEGRAM\\_ALLOWED\\_USER\\_IDS first, "
                "otherwise startup re-seeds them.",
                parse_mode="Markdown",
            )
            return
        await repo.set_active(target_id, False)

    await update.message.reply_text(f"🚫 `{target_id}` can no longer use the bot.", parse_mode="Markdown")


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("digest", digest_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("contacts", contacts_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("whoami", whoami_command))
    app.add_handler(CommandHandler("digest_on", digest_on_command))
    app.add_handler(CommandHandler("digest_off", digest_off_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
