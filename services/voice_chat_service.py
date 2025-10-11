"""Voice chat service for handling audio conversations."""

import logging
from collections.abc import AsyncIterator

from clients.openai_client import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TTS_VOICE,
    openai_client,
)

logger = logging.getLogger(__name__)


class VoiceChatService:
    """Service for managing voice chat conversations."""

    def __init__(self) -> None:
        """Initialize voice chat service."""
        self.client = openai_client
        # Store conversation history per session
        self.conversations: dict[str, list[dict[str, str]]] = {}
        # Store voice preference per session
        self.session_voices: dict[str, str] = {}

    def create_session(self, session_id: str) -> None:
        """
        Create a new conversation session.

        Args:
            session_id: Unique session identifier
        """
        # Initialize with default system prompt
        self.conversations[session_id] = [{
            "role": "system",
            "content": DEFAULT_SYSTEM_PROMPT
        }]
        # Set default voice
        self.session_voices[session_id] = DEFAULT_TTS_VOICE
        logger.info(f"Created voice chat session: {session_id}")

    def get_conversation_history(self, session_id: str) -> list[dict[str, str]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation messages
        """
        return self.conversations.get(session_id, [])

    def add_to_history(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to conversation history.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        self.conversations[session_id].append({
            "role": role,
            "content": content
        })

    def clear_session(self, session_id: str) -> None:
        """
        Clear a conversation session.

        Args:
            session_id: Session identifier
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
        if session_id in self.session_voices:
            del self.session_voices[session_id]
        logger.info(f"Cleared voice chat session: {session_id}")

    async def process_audio_to_text(self, audio_data: bytes, format: str = "wav") -> str:
        """
        Transcribe audio to text.

        Args:
            audio_data: Raw audio bytes
            format: Audio format

        Returns:
            Transcribed text
        """
        try:
            text = await self.client.transcribe_audio(audio_data, format)
            logger.info(f"Transcribed audio: {text[:100]}...")
            return text
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise

    async def generate_text_response(self, session_id: str, user_text: str) -> str:
        """
        Generate a text response for user input.

        Args:
            session_id: Session identifier
            user_text: User input text

        Returns:
            Generated response text
        """
        try:
            # Get conversation history
            history = self.get_conversation_history(session_id)

            # Add user message to history
            self.add_to_history(session_id, "user", user_text)

            # Generate response
            response_text = await self.client.generate_response(
                user_text,
                conversation_history=history
            )

            # Add assistant response to history
            self.add_to_history(session_id, "assistant", response_text)

            logger.info(f"Generated response: {response_text[:100]}...")
            return response_text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def get_session_voice(self, session_id: str) -> str:
        """
        Get the voice for a session.

        Args:
            session_id: Session identifier

        Returns:
            Voice identifier
        """
        return self.session_voices.get(session_id, DEFAULT_TTS_VOICE)

    async def text_to_audio(self, session_id: str, text: str) -> bytes:
        """
        Convert text to audio using session's voice.

        Args:
            session_id: Session identifier
            text: Text to convert

        Returns:
            Audio bytes
        """
        try:
            voice = self.get_session_voice(session_id)
            audio = await self.client.text_to_speech(text, voice)
            logger.info(f"Generated audio for text: {text[:100]}...")
            return audio
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            raise

    async def text_to_audio_stream(self, session_id: str, text: str) -> AsyncIterator[bytes]:
        """
        Convert text to audio and stream it using session's voice.

        Args:
            session_id: Session identifier
            text: Text to convert

        Yields:
            Audio chunks
        """
        try:
            voice = self.get_session_voice(session_id)
            async for chunk in self.client.text_to_speech_stream(text, voice):
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            raise

    async def process_voice_message(
        self,
        session_id: str,
        audio_data: bytes,
        format: str = "wav"
    ) -> tuple[str, str, bytes]:
        """
        Process a complete voice message: audio -> text -> response -> audio.

        Args:
            session_id: Session identifier
            audio_data: Input audio bytes
            format: Audio format

        Returns:
            Tuple of (transcribed_text, response_text, response_audio)
        """
        # Step 1: Transcribe audio to text
        transcribed_text = await self.process_audio_to_text(audio_data, format)

        # Step 2: Generate text response
        response_text = await self.generate_text_response(session_id, transcribed_text)

        # Step 3: Convert response to audio using session's voice
        response_audio = await self.text_to_audio(session_id, response_text)

        return transcribed_text, response_text, response_audio


# Global service instance
voice_chat_service = VoiceChatService()

