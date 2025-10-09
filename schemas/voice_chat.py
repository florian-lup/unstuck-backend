"""Voice Chat schemas for OpenAI Realtime API."""

from enum import Enum

from pydantic import BaseModel, Field


class VoiceOption(str, Enum):
    """Available voice options for OpenAI Realtime API."""

    ALLOY = "alloy"
    ECHO = "echo"
    SHIMMER = "shimmer"
    ASH = "ash"
    BALLAD = "ballad"
    CORAL = "coral"
    SAGE = "sage"
    VERSE = "verse"


class VoiceChatSessionRequest(BaseModel):
    """Request model for creating a voice chat session."""

    game: str | None = Field(
        default=None,
        description=(
            "The game the user is currently playing (auto-detected by Electron client). "
            "Examples: 'Elden Ring', 'Valorant', 'League of Legends'"
        ),
        max_length=200,
    )

    def get_instructions(self) -> str:
        """
        Generate AI instructions based on the detected game.
        
        If a game is detected, creates game-specific instructions.
        Otherwise, returns generic gaming assistant instructions.
        """
        if self.game:
            return (
                f"You are a helpful gaming assistant specializing in {self.game}. "
                f"You help players with tips, strategies, walkthroughs, builds, "
                f"and gameplay questions specifically for {self.game}. "
                "Be conversational, friendly, and enthusiastic. "
                "Provide accurate information and helpful guidance. "
                "If asked about something outside the game, politely redirect to game-related topics."
            )
        
        return (
            "You are a helpful gaming assistant. You help gamers with tips, "
            "strategies, game information, and general gaming questions. "
            "Be conversational, friendly, and enthusiastic about gaming."
        )


class VoiceChatSessionConfig(BaseModel):
    """Session configuration to send after WebSocket connection."""

    voice: str = Field(
        default="alloy",
        description="Voice to use for audio responses",
    )
    instructions: str = Field(
        ...,
        description="System instructions for the AI assistant",
    )
    modalities: list[str] = Field(
        default=["text", "audio"],
        description="Modalities to use (text, audio)",
    )
    turn_detection: dict[str, str | float] = Field(
        default={"type": "server_vad"},
        description="Turn detection configuration",
    )


class VoiceChatSessionResponse(BaseModel):
    """Response model containing ephemeral token for voice chat."""

    client_secret: str = Field(
        ...,
        description="Ephemeral token for WebSocket connection (use as Bearer token)",
    )
    ephemeral_key_id: str = Field(
        ...,
        description="Unique identifier for the ephemeral key",
    )
    model: str = Field(
        ...,
        description="OpenAI model being used for the session",
    )
    expires_at: int = Field(
        ...,
        description="Unix timestamp when the token expires",
    )
    websocket_url: str = Field(
        default="wss://api.openai.com/v1/realtime",
        description="WebSocket URL to connect to (query params: ?model=MODEL_NAME)",
    )
    session_config: VoiceChatSessionConfig = Field(
        ...,
        description="Session configuration to send via WebSocket after connection (as session.update event)",
    )
    connection_instructions: dict[str, str] = Field(
        default={
            "url": "wss://api.openai.com/v1/realtime",
            "auth_header": "Authorization: Bearer <client_secret>",
            "query_param": "?model=gpt-realtime-mini-2025-10-06",
            "note": "Connect using WebSocket with the client_secret as Bearer token",
        },
        description="Instructions for connecting to the Realtime API",
    )


class VoiceChatError(BaseModel):
    """Error response for voice chat operations."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    request_id: str | None = Field(None, description="Request ID for debugging")

