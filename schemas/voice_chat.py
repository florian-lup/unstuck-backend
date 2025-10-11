"""Schemas for voice chat operations."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""

    # Client -> Server
    AUDIO_CHUNK = "audio_chunk"
    AUDIO_END = "audio_end"
    START_SESSION = "start_session"
    END_SESSION = "end_session"

    # Server -> Client
    TRANSCRIPTION = "transcription"
    RESPONSE_TEXT = "response_text"
    AUDIO_RESPONSE = "audio_response"
    AUDIO_STREAM_START = "audio_stream_start"
    AUDIO_STREAM_CHUNK = "audio_stream_chunk"
    AUDIO_STREAM_END = "audio_stream_end"
    ERROR = "error"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


class VoiceMessageBase(BaseModel):
    """Base voice chat message."""

    type: MessageType = Field(..., description="Message type")


class StartSessionMessage(VoiceMessageBase):
    """Start a new voice chat session."""

    type: Literal[MessageType.START_SESSION] = MessageType.START_SESSION
    session_id: str = Field(..., description="Unique session identifier")


class AudioChunkMessage(VoiceMessageBase):
    """Audio chunk from client."""

    type: Literal[MessageType.AUDIO_CHUNK] = MessageType.AUDIO_CHUNK
    session_id: str = Field(..., description="Session identifier")
    audio_data: str = Field(..., description="Base64 encoded audio data")
    format: str = Field(default="wav", description="Audio format")


class AudioEndMessage(VoiceMessageBase):
    """Signal end of audio input."""

    type: Literal[MessageType.AUDIO_END] = MessageType.AUDIO_END
    session_id: str = Field(..., description="Session identifier")


class EndSessionMessage(VoiceMessageBase):
    """End voice chat session."""

    type: Literal[MessageType.END_SESSION] = MessageType.END_SESSION
    session_id: str = Field(..., description="Session identifier")


class TranscriptionMessage(VoiceMessageBase):
    """Transcription result."""

    type: Literal[MessageType.TRANSCRIPTION] = MessageType.TRANSCRIPTION
    session_id: str = Field(..., description="Session identifier")
    text: str = Field(..., description="Transcribed text")


class ResponseTextMessage(VoiceMessageBase):
    """Generated text response."""

    type: Literal[MessageType.RESPONSE_TEXT] = MessageType.RESPONSE_TEXT
    session_id: str = Field(..., description="Session identifier")
    text: str = Field(..., description="Response text")


class AudioResponseMessage(VoiceMessageBase):
    """Audio response (complete)."""

    type: Literal[MessageType.AUDIO_RESPONSE] = MessageType.AUDIO_RESPONSE
    session_id: str = Field(..., description="Session identifier")
    audio_data: str = Field(..., description="Base64 encoded audio data")
    format: str = Field(default="pcm", description="Audio format")


class AudioStreamStartMessage(VoiceMessageBase):
    """Start of audio stream."""

    type: Literal[MessageType.AUDIO_STREAM_START] = MessageType.AUDIO_STREAM_START
    session_id: str = Field(..., description="Session identifier")


class AudioStreamChunkMessage(VoiceMessageBase):
    """Audio stream chunk."""

    type: Literal[MessageType.AUDIO_STREAM_CHUNK] = MessageType.AUDIO_STREAM_CHUNK
    session_id: str = Field(..., description="Session identifier")
    audio_data: str = Field(..., description="Base64 encoded audio chunk")


class AudioStreamEndMessage(VoiceMessageBase):
    """End of audio stream."""

    type: Literal[MessageType.AUDIO_STREAM_END] = MessageType.AUDIO_STREAM_END
    session_id: str = Field(..., description="Session identifier")


class ErrorMessage(VoiceMessageBase):
    """Error message."""

    type: Literal[MessageType.ERROR] = MessageType.ERROR
    session_id: str | None = Field(None, description="Session identifier")
    error: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code")


class SessionStartedMessage(VoiceMessageBase):
    """Session started confirmation."""

    type: Literal[MessageType.SESSION_STARTED] = MessageType.SESSION_STARTED
    session_id: str = Field(..., description="Session identifier")


class SessionEndedMessage(VoiceMessageBase):
    """Session ended confirmation."""

    type: Literal[MessageType.SESSION_ENDED] = MessageType.SESSION_ENDED
    session_id: str = Field(..., description="Session identifier")

