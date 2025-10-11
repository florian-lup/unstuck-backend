"""OpenAI client for voice chat operations."""

import io
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from core.config import settings

# Voice chat configuration
DEFAULT_TTS_VOICE = "alloy"
DEFAULT_SYSTEM_PROMPT = "You are a helpful gaming assistant. Provide concise, clear, and helpful responses to gaming-related questions."


class OpenAIClient:
    """Client for interacting with OpenAI's voice APIs."""

    def __init__(self) -> None:
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe_audio(self, audio_data: bytes, format: str = "wav") -> str:
        """
        Transcribe audio to text using OpenAI's Whisper model.

        Args:
            audio_data: Raw audio bytes
            format: Audio format (wav, mp3, etc.)

        Returns:
            Transcribed text
        """
        # Create a file-like object from bytes
        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"audio.{format}"

        # Call transcription API
        transcript = await self.client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
        )

        return transcript.text

    async def generate_response(self, text: str, conversation_history: list[dict[str, Any]] | None = None) -> str:
        """
        Generate a response using OpenAI's Responses API.

        Args:
            text: User input text
            conversation_history: Optional conversation history (if None, uses default system prompt)

        Returns:
            Generated response text
        """
        # Build messages for the Responses API
        messages: list[ChatCompletionMessageParam]
        if conversation_history is None:
            # Use default system prompt if no history provided
            messages = [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        else:
            messages = conversation_history.copy()  # type: ignore
            messages.append({"role": "user", "content": text})

        # Call Responses API
        response = await self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages,
        )

        return response.choices[0].message.content or ""

    async def text_to_speech(self, text: str, voice: str | None = None) -> bytes:
        """
        Convert text to speech using OpenAI's TTS model.

        Args:
            text: Text to convert to speech
            voice: Voice to use (if None, uses DEFAULT_TTS_VOICE)

        Returns:
            Audio bytes in the response format
        """
        # Use default voice if not specified
        tts_voice = voice or DEFAULT_TTS_VOICE
        
        # Call TTS API
        response = await self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=tts_voice,
            input=text,
            response_format="pcm",  # Raw PCM for streaming
        )

        # Return audio content as bytes
        audio_bytes = b""
        async for chunk in response.iter_bytes():  # type: ignore
            audio_bytes += chunk

        return audio_bytes

    async def text_to_speech_stream(self, text: str, voice: str | None = None) -> AsyncIterator[bytes]:
        """
        Convert text to speech and stream the audio.

        Args:
            text: Text to convert to speech
            voice: Voice to use (if None, uses DEFAULT_TTS_VOICE)

        Yields:
            Audio chunks as bytes
        """
        # Use default voice if not specified
        tts_voice = voice or DEFAULT_TTS_VOICE
        
        response = await self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=tts_voice,
            input=text,
            response_format="pcm",
        )

        async for chunk in response.iter_bytes():  # type: ignore
            yield chunk


# Global client instance
openai_client = OpenAIClient()

