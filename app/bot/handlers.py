import base64

from telegram import Update
from telegram.ext import ContextTypes

from app.agent.orchestrator import ConferenceAgent
from app.bot.auth import authorize
from app.core.database import session_scope
from app.core.logging import logger
from app.services.conversation import load_history, save_message
from app.services.transcription import transcription_service


COMPLEX_KEYWORDS = (
    "brief me", "summary", "digest", "enrich", "draft", "prepare",
    "follow up", "tell me about", "what do i know",
)


def is_complex_request(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in COMPLEX_KEYWORDS) or len(text) > 200


# Thin aliases kept so the handlers below read unchanged; the implementation
# moved to app/services/conversation.py so the web chat shares one history.
get_conversation_history = load_history
save_message_to_history = save_message


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await authorize(update) is None:
        return
    user_id = update.effective_user.id

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    text = update.message.text or ""
    if is_complex_request(text):
        await update.message.reply_text("⏳ On it...")

    history = await get_conversation_history(str(user_id), limit=20)

    async with session_scope() as db:
        agent = ConferenceAgent(db)
        response = await agent.process_message(user_message=text, message_history=history)

    await save_message_to_history(str(user_id), "user", text)
    await save_message_to_history(str(user_id), "assistant", response)

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await authorize(update) is None:
        return
    user_id = update.effective_user.id

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

    async with session_scope() as db:
        agent = ConferenceAgent(db)
        response = await agent.process_message(user_message=user_message, message_history=history)

    await save_message_to_history(str(user_id), "user", user_message)
    await save_message_to_history(str(user_id), "assistant", response)

    await update.message.reply_text(f"_Heard: {transcript}_", parse_mode="Markdown")
    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await authorize(update) is None:
        return
    user_id = update.effective_user.id

    await update.message.reply_text("📸 Reading badge...")

    # Get highest resolution version of the photo
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    image_bytes = await photo_file.download_as_bytearray()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Any caption the user added ("met at the AI panel", "potential investor")
    caption = update.message.caption or ""

    history = await get_conversation_history(str(user_id), limit=20)

    async with session_scope() as db:
        agent = ConferenceAgent(db)
        response = await agent.process_message(
            user_message=f"[Badge photo]{f': {caption}' if caption else ''}",
            message_history=history,
            image_b64=image_b64,
            image_media_type="image/jpeg",
        )

    await save_message_to_history(str(user_id), "user", f"[Badge photo] {caption}".strip())
    await save_message_to_history(str(user_id), "assistant", response)

    await update.message.reply_text(response, parse_mode="Markdown")