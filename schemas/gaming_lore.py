"""Gaming Lore schemas for request/response validation."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """Individual message in a conversation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class GamingLoreRequest(BaseModel):
    """Request schema for Gaming Lore queries."""

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
        default=None, description="ID to track conversation across requests"
    )
    conversation_history: list[ConversationMessage] | None = Field(
        default=None, description="Previous messages in the conversation"
    )


class SearchResult(BaseModel):
    """Individual search result from gaming search."""

    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str | None = Field(default=None, description="Content snippet")
    date: str | None = Field(default=None, description="Publication date")


class UsageStats(BaseModel):
    """Token usage statistics from OpenAI API response."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="Total number of tokens used")
    search_queries_performed: int | None = Field(
        default=None, description="Number of search queries performed via tool calling"
    )


class GamingLoreResponse(BaseModel):
    """Response schema for Gaming Lore queries."""

    id: str = Field(..., description="Unique response ID")
    conversation_id: UUID = Field(
        default_factory=uuid4, description="ID to track conversation"
    )
    model: str = Field(..., description="Model used for the response (gpt-4o-mini)")
    created: int = Field(..., description="Unix timestamp of response creation")
    content: str = Field(..., description="AI-generated lore response content")
    search_results: list[SearchResult] | None = Field(
        default=None, description="Search results used to generate the response (if any)"
    )
    usage: UsageStats | None = Field(default=None, description="Token usage statistics")
    finish_reason: str | None = Field(
        default=None, description="Reason the generation finished"
    )
    tool_calls_made: int = Field(
        default=0, description="Number of search tool calls made during generation"
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
