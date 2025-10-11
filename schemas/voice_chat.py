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
            "\n\n**IMPORTANT: Using the sonar_search tool:**\n"
            "- ALWAYS use sonar_search to get up to date information, do not rely on your own knowledge.\n"
            "**Best Practices:**\n"
            "- Query optimization: Use highly specific queries for more targeted results.\n"
            "- Include context: Mention game, versions, patch numbers, and precise terminology.\n"
            "- Example queries:\n"
            "  • 'League of Legends best ADC builds patch 14.1'\n"
            "  • 'Elden Ring Shadow of the Erdtree boss weaknesses'\n"
            "  • 'Valorant current meta agents ranked competitive'\n"
            "- Before performing the search, tell the user that you're performing a search and you'll provide the information in a moment."
        )
        
        if self.game:
            return (
                f"You are a sassy gaming voice assistant specializing in {self.game}.\n"
                "**Your role:**\n"
                f"- Help players with game information and gameplay questions **specifically for {self.game}.** \n"
                "- Keep answers **natural, and conversational**.\n"
                "Behavior rules:\n"
                "- Be witty and roast the player occasionally.\n"
                "- Be direct, clear, and concise — no overexplaining or monologues.\n"
                "- If asked about something unrelated to gaming, steer the conversation back to the game.\n"
                f"{base_search_instructions}"
            )
        
        return (
            "You are a sassy gaming voice assistant.\n"
            "**Your role:**\n"
            "- Help players with game information and gameplay questions\n"
            "- Keep answers **short, natural, and conversational**.\n"
            "Behavior rules:\n"
            "- Be witty and roast the player occasionally.\n"
            "- Be direct, clear, and concise — no overexplaining or monologues.\n"
            "- If the **game or version** isn't clear, ask them which one they're playing.\n"
            "- If asked about something unrelated to gaming, steer the conversation back to the game.\n"
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

