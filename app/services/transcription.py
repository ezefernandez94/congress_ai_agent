import io

from openai import AsyncOpenAI

from app.core.config import settings


class TranscriptionService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio_bytes: bytes | bytearray, filename: str = "voice.ogg") -> str:
        audio_file = io.BytesIO(bytes(audio_bytes))
        audio_file.name = filename

        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return response.text


transcription_service = TranscriptionService()
