"""Search schemas for request/response validation."""

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request schema for Perplexity Search queries."""

    query: str | list[str] = Field(
        ..., description="Search query or list of queries for multi-query search"
    )
    max_results: int = Field(
        default=10, ge=1, le=50, description="Maximum number of results to return"
    )
    max_tokens_per_page: int = Field(
        default=2048, ge=256, le=4096, description="Content extraction limit per page"
    )


class SearchResultItem(BaseModel):
    """Individual search result item."""

    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str | None = Field(default=None, description="Content snippet")
    date: str | None = Field(default=None, description="Publication date")


class SearchResponse(BaseModel):
    """Response schema for Search queries."""

    id: str = Field(..., description="Unique search response ID")
    results: list[SearchResultItem] | list[list[SearchResultItem]] = Field(
        default_factory=list, 
        description="Search results. For single query: flat list. For multi-query: list of lists, one per query."
    )
    query: str | list[str] = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results returned")
    created: int = Field(..., description="Unix timestamp of response creation")
    is_multi_query: bool = Field(
        default=False, description="Whether this was a multi-query search"
    )


class SearchErrorResponse(BaseModel):
    """Error response schema for search."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    query: str | list[str] | None = Field(
        default=None, description="Original query that failed"
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )
