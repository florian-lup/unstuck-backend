"""Gaming search service with conversation management."""

import time
from typing import Any
from uuid import UUID, uuid4

from clients.perplexity_client import perplexity_client
from schemas.gaming_search import (
    ConversationMessage,
    GamingSearchRequest,
    GamingSearchResponse,
    SearchResult,
    UsageStats,
)


class ConversationManager:
    """Manages gaming search conversations in memory."""

    def __init__(self) -> None:
        """Initialize the conversation manager."""
        self._conversations: dict[UUID, list[ConversationMessage]] = {}
        self._conversation_metadata: dict[UUID, dict[str, Any]] = {}

    def create_conversation(self, conversation_id: UUID | None = None) -> UUID:
        """Create a new conversation or return existing ID."""
        if conversation_id is None:
            conversation_id = uuid4()

        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
            self._conversation_metadata[conversation_id] = {
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }

        return conversation_id

    def add_message(self, conversation_id: UUID, role: str, content: str) -> None:
        """Add a message to the conversation."""
        if conversation_id not in self._conversations:
            self.create_conversation(conversation_id)

        message = ConversationMessage(role=role, content=content)
        self._conversations[conversation_id].append(message)
        self._conversation_metadata[conversation_id]["updated_at"] = int(time.time())

    def get_conversation(self, conversation_id: UUID) -> list[ConversationMessage]:
        """Get all messages from a conversation."""
        return self._conversations.get(conversation_id, [])

    def get_conversation_history(
        self, conversation_id: UUID, include_system: bool = False
    ) -> list[dict[str, Any]]:
        """Get conversation history formatted for Perplexity API."""
        messages = self.get_conversation(conversation_id)

        if not include_system:
            # Filter out system messages for API calls
            messages = [msg for msg in messages if msg.role != "system"]

        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def clear_conversation(self, conversation_id: UUID) -> bool:
        """Clear a conversation."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            del self._conversation_metadata[conversation_id]
            return True
        return False

    def list_conversations(self) -> list[UUID]:
        """List all active conversation IDs."""
        return list(self._conversations.keys())


class GamingSearchService:
    """Service for handling gaming search requests with conversation management."""

    def __init__(self) -> None:
        """Initialize the gaming search service."""
        self._conversation_manager = ConversationManager()

    def search(self, request: GamingSearchRequest) -> GamingSearchResponse:
        """
        Perform a gaming search with conversation context.

        Args:
            request: Gaming search request

        Returns:
            Gaming search response
        """
        # Create or get conversation
        conversation_id = self._conversation_manager.create_conversation(
            request.conversation_id
        )

        # Build conversation history for API
        conversation_history = []
        if request.conversation_history:
            # Use provided history
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        else:
            # Use stored conversation history
            conversation_history = self._conversation_manager.get_conversation_history(
                conversation_id, include_system=False
            )

        try:
            # Call Perplexity API
            response = perplexity_client.gaming_search(
                query=request.query,
                conversation_history=conversation_history,
                temperature=request.temperature,
            )

            # Store user message in conversation
            self._conversation_manager.add_message(
                conversation_id, "user", request.query
            )

            # Extract response data
            choice = response.choices[0]
            assistant_content = choice.message.content

            # Store assistant response in conversation
            self._conversation_manager.add_message(
                conversation_id, "assistant", assistant_content
            )

            # Parse search results
            search_results = []
            if hasattr(response, "search_results") and response.search_results:
                search_results = [
                    SearchResult(
                        title=result.title,
                        url=result.url,
                        date=getattr(result, "date", None),
                    )
                    for result in response.search_results
                ]

            # Parse usage statistics
            usage_stats = None
            if hasattr(response, "usage") and response.usage:
                usage_data = response.usage
                usage_stats = UsageStats(
                    prompt_tokens=usage_data.prompt_tokens,
                    completion_tokens=usage_data.completion_tokens,
                    total_tokens=usage_data.total_tokens,
                    search_context_size=getattr(
                        usage_data, "search_context_size", None
                    ),
                    citation_tokens=getattr(usage_data, "citation_tokens", None),
                    num_search_queries=getattr(usage_data, "num_search_queries", None),
                )

            return GamingSearchResponse(
                id=response.id,
                conversation_id=conversation_id,
                model=response.model,
                created=response.created,
                content=assistant_content,
                search_results=search_results,
                usage=usage_stats,
                finish_reason=getattr(choice, "finish_reason", None),
            )

        except Exception as e:
            # Log the error and re-raise
            # In a production system, you'd want proper logging here
            raise RuntimeError(f"Gaming search failed: {e!s}") from e

    def get_conversation_history(
        self, conversation_id: UUID
    ) -> list[ConversationMessage]:
        """Get conversation history."""
        return self._conversation_manager.get_conversation(conversation_id)

    def clear_conversation(self, conversation_id: UUID) -> bool:
        """Clear a conversation."""
        return self._conversation_manager.clear_conversation(conversation_id)

    def list_conversations(self) -> list[UUID]:
        """List all active conversations."""
        return self._conversation_manager.list_conversations()


# Global service instance
gaming_search_service = GamingSearchService()
