"""Gaming Chat schemas for request/response validation."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from schemas.common import ConversationMessage


class GamingChatRequest(BaseModel):
    """Request schema for Gaming Chat queries."""

    query: str = Field(
        ..., min_length=1, max_length=500, description="Gaming Chat query"
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
    # temperature removed - now handled in config


class SearchResult(BaseModel):
    """Individual search result from Perplexity."""

    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    date: str | None = Field(default=None, description="Publication date")


class UsageStats(BaseModel):
    """Token usage statistics from the API response."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="Total number of tokens used")
    search_context_size: str | None = Field(
        default=None, description="Search context size used"
    )
    citation_tokens: int | None = Field(
        default=None, description="Number of tokens used for citations"
    )
    num_search_queries: int | None = Field(
        default=None, description="Number of search queries performed"
    )


class RequestLimitInfo(BaseModel):
    """Request limit information for the user's subscription tier."""

    remaining_requests: int = Field(..., description="Number of requests remaining")
    max_requests: int = Field(..., description="Maximum requests allowed")
    limit_type: str = Field(..., description="Type of limit: 'lifetime' or 'monthly'")
    reset_date: str | None = Field(
        default=None, description="ISO date when monthly limit resets (monthly tier only)"
    )


class GamingChatResponse(BaseModel):
    """Response schema for Gaming Chat queries."""

    id: str = Field(..., description="Unique response ID")
    conversation_id: UUID = Field(
        default_factory=uuid4, description="ID to track conversation"
    )
    model: str = Field(..., description="Model used for the response")
    created: int = Field(..., description="Unix timestamp of response creation")
    content: str = Field(..., description="AI-generated response content")
    search_results: list[SearchResult] | None = Field(
        default=None, description="Search results used to generate the response"
    )
    usage: UsageStats | None = Field(default=None, description="Token usage statistics")
    finish_reason: str | None = Field(
        default=None, description="Reason the generation finished"
    )
    request_limit_info: RequestLimitInfo = Field(
        ..., description="Request limit information for user's tier"
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


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )
