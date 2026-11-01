import base64

from telegram import Update
from telegram.ext import ContextTypes

from app.agent.orchestrator import ConferenceAgent
from app.bot.auth import authorize
from app.core.logging import logger
from app.core.tenancy import Caller, caller_session
from app.services.conversation import load_history, save_message
from app.services.transcription import transcription_service

COMPLEX_KEYWORDS = (
    "brief me", "summary", "digest", "enrich", "draft", "prepare",
    "follow up", "tell me about", "what do i know",
)


def is_complex_request(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in COMPLEX_KEYWORDS) or len(text) > 200


async def _run_agent(caller: Caller, user_message: str, saved_as: str, **agent_kwargs) -> str:
    """One agent turn on a session scoped to the caller's workspace (ADR-018).

    History is read and written on the same session as the agent's tools, so the turn sees and
    records only the caller's workspace. History stays keyed by Telegram user ID (ADR-011).
    """
    user_key = str(caller.user.telegram_user_id)
    async with caller_session(caller) as db:
        history = await load_history(user_key, limit=20, db=db)
        response = await ConferenceAgent(db).process_message(
            user_message=user_message, message_history=history, **agent_kwargs
        )
        await save_message(user_key, "user", saved_as, db=db)
        await save_message(user_key, "assistant", response, db=db)
    return response


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caller = await authorize(update)
    if caller is None:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    text = update.message.text or ""
    if is_complex_request(text):
        await update.message.reply_text("⏳ On it...")

    response = await _run_agent(caller, text, saved_as=text)

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caller = await authorize(update)
    if caller is None:
        return

    await update.message.reply_text("🎙 Transcribing...")

    voice_file = await context.bot.get_file(update.message.voice.file_id)
    audio_bytes = await voice_file.download_as_bytearray()

    try:
        transcript = await transcription_service.transcribe(audio_bytes)
    except Exception as e:  # noqa: BLE001 - any Whisper or download failure gets the same retry reply
        logger.error("transcription_failed", error=str(e))
        await update.message.reply_text("Sorry, I couldn't transcribe that voice note. Please try again.")
        return

    user_message = f"[Voice note]: {transcript}"
    response = await _run_agent(caller, user_message, saved_as=user_message)

    await update.message.reply_text(f"_Heard: {transcript}_", parse_mode="Markdown")
    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caller = await authorize(update)
    if caller is None:
        return

    await update.message.reply_text("📸 Reading badge...")

    # Get highest resolution version of the photo
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    image_bytes = await photo_file.download_as_bytearray()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Any caption the user added ("met at the AI panel", "potential investor")
    caption = update.message.caption or ""

    response = await _run_agent(
        caller,
        f"[Badge photo]{f': {caption}' if caption else ''}",
        saved_as=f"[Badge photo] {caption}".strip(),
        image_b64=image_b64,
        image_media_type="image/jpeg",
    )

    await update.message.reply_text(response, parse_mode="Markdown")