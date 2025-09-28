"""Gaming Lore schemas for request/response validation with Responses API support."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """Individual message in a conversation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class GamingLoreRequest(BaseModel):
    """Request schema for Gaming Lore queries with OpenAI conversation management."""

    query: str = Field(
        ..., min_length=1, max_length=1000, description="Gaming lore query about story, characters, world-building, etc."
    )
    game: str = Field(
        ..., min_length=1, max_length=100, description="Game name to provide context"
    )
    version: str | None = Field(
        default=None, max_length=50, description="Game version (optional)"
    )
    conversation_id: UUID | None = Field(
        default=None, description="ID to continue existing conversation (OpenAI handles conversation state automatically)"
    )




class UsageStats(BaseModel):
    """Token usage statistics from OpenAI Responses API with enhanced metadata."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="Total number of tokens used")
    search_queries_performed: int | None = Field(
        default=None, description="Number of search queries performed via tool calling"
    )
    structured_output_used: bool = Field(
        default=True, description="Whether structured outputs were used"
    )
    responses_api_used: bool = Field(
        default=True, description="Whether the Responses API was used"
    )


class GamingLoreResponse(BaseModel):
    """Enhanced response schema for Gaming Lore queries with Responses API features."""

    id: str = Field(..., description="Unique response ID")
    conversation_id: UUID = Field(
        default_factory=uuid4, description="ID to track conversation"
    )
    model: str = Field(..., description="Model used for the response (gpt-5-mini-2025-08-07)")
    created: int = Field(..., description="Unix timestamp of response creation")
    content: str = Field(..., description="AI-generated lore response content in markdown format")
    usage: UsageStats | None = Field(default=None, description="Token usage statistics")
    finish_reason: str | None = Field(
        default=None, description="Reason the generation finished"
    )
    tool_calls_made: int = Field(
        default=0, description="Number of search tool calls made during generation"
    )
    sources_used: list[str] = Field(
        default_factory=list, description="List of web sources or references used in the response"
    )


class ConversationHistoryRequest(BaseModel):
    """Request schema for retrieving conversation history."""

    conversation_id: UUID = Field(..., description="Conversation ID to retrieve")


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""

    conversation_id: UUID = Field(..., description="Conversation ID")
    messages: list[ConversationMessage] = Field(
        ..., description="All messages in the conversation"
    )
    created_at: int = Field(..., description="Unix timestamp of conversation start")
    updated_at: int = Field(..., description="Unix timestamp of last update")


class GamingLoreErrorResponse(BaseModel):
    """Error response schema for gaming lore."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    query: str | None = Field(default=None, description="Original query that failed")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )
