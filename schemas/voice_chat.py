"""Voice Chat schemas for OpenAI Realtime API."""

from enum import Enum

from pydantic import BaseModel, Field


class VoiceOption(str, Enum):
    """Available voice options for OpenAI Realtime API."""

    MARIN = "marin"  # Default - warm and friendly
    CEDAR = "cedar"  # Alternative - clear and professional


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
        base_search_instructions = (
            "\n\n**IMPORTANT: Using the gaming_search tool:**\n"
            "- ALWAYS use gaming_search when:\n"
            "you don't know the answer.\n"
            "you don't have the information for this version of the game.\n"
            "your knowledge might be outdated.\n"
            "you're uncertain.\n"
            "- Include the game name in your search query for better results."
        )
        
        if self.game:
            return (
                f"You are a helpful gaming assistant specializing in {self.game}. "
                f"You help players with game information"
                f"and gameplay questions specifically for {self.game}. "
                "Be conversational, friendly, and enthusiastic. "
                "Provide accurate information and helpful guidance. "
                "If asked about something outside the game, politely redirect to game-related topics."
                f"{base_search_instructions}"
            )
        
        return (
            "You are a helpful gaming assistant. You help players with game information, and general gaming questions. "
            "Be conversational, friendly, and enthusiastic about gaming."
            f"{base_search_instructions}"
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


class ToolCallRequest(BaseModel):
    """Request model for executing a tool call from the Realtime API."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: dict = Field(..., description="Arguments passed to the tool")
    call_id: str | None = Field(None, description="Call ID from OpenAI for tracking")


class ToolCallResponse(BaseModel):
    """Response model for tool call execution."""

    call_id: str | None = Field(None, description="Call ID for tracking")
    result: dict = Field(..., description="Result of the tool execution")
    error: str | None = Field(None, description="Error message if tool execution failed")

