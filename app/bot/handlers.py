from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from app.agent.orchestrator import ConferenceAgent
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.conversation import ConversationMessage
from app.services.transcription import transcription_service

COMPLEX_KEYWORDS = (
    "brief me", "summary", "digest", "enrich", "draft", "prepare",
    "follow up", "tell me about", "what do i know",
)


def is_complex_request(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in COMPLEX_KEYWORDS) or len(text) > 200


async def get_conversation_history(user_id: str, limit: int = 20) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def save_message_to_history(user_id: str, role: str, content: str) -> None:
    async with AsyncSessionLocal() as db:
        msg = ConversationMessage(user_id=user_id, role=role, content=content)
        db.add(msg)
        await db.commit()


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != settings.telegram_allowed_user_id:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    text = update.message.text or ""
    if is_complex_request(text):
        await update.message.reply_text("⏳ On it...")

    history = await get_conversation_history(str(user_id), limit=20)

    async with AsyncSessionLocal() as db:
        agent = ConferenceAgent(db)
        response = await agent.process_message(user_message=text, message_history=history)

    await save_message_to_history(str(user_id), "user", text)
    await save_message_to_history(str(user_id), "assistant", response)

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != settings.telegram_allowed_user_id:
        return

    await update.message.reply_text("🎙 Transcribing...")

    voice_file = await context.bot.get_file(update.message.voice.file_id)
    audio_bytes = await voice_file.download_as_bytearray()

    try:
        transcript = await transcription_service.transcribe(audio_bytes)
    except Exception as e:
        logger.error("transcription_failed", error=str(e))
        await update.message.reply_text("Sorry, I couldn't transcribe that voice note. Please try again.")
        return

    user_message = f"[Voice note]: {transcript}"
    history = await get_conversation_history(str(user_id), limit=20)

    async with AsyncSessionLocal() as db:
        agent = ConferenceAgent(db)
        response = await agent.process_message(user_message=user_message, message_history=history)

    await save_message_to_history(str(user_id), "user", user_message)
    await save_message_to_history(str(user_id), "assistant", response)

    await update.message.reply_text(f"_Heard: {transcript}_", parse_mode="Markdown")
    await update.message.reply_text(response, parse_mode="Markdown")
