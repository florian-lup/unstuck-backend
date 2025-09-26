"""Gaming search service with database-backed conversation management."""

import logging
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from clients.perplexity_client import perplexity_client
from database.models import Conversation
from database.service import DatabaseService
from schemas.gaming_search import (
    ConversationMessage,
    GamingSearchRequest,
    GamingSearchResponse,
    SearchResult,
    UsageStats,
)

logger = logging.getLogger(__name__)


class GamingSearchService:
    """Service for handling gaming search requests with database-backed conversation management."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the gaming search service with database session."""
        self.db_service = DatabaseService(db_session)

    async def search(
        self, request: GamingSearchRequest, user_id: UUID, auth0_user_id: str
    ) -> GamingSearchResponse:
        """
        Perform a gaming search with conversation context.

        Args:
            request: Gaming search request
            user_id: User ID from Auth0 token (for security)
            auth0_user_id: Auth0 user identifier

        Returns:
            Gaming search response
        """
        try:
            # Ensure user exists in database
            await self.db_service.get_or_create_user(auth0_user_id)

            # Get or create conversation
            conversation: Conversation
            if request.conversation_id:
                # Use existing conversation (verify user owns it)
                existing_conversation = (
                    await self.db_service.get_conversation_with_messages(
                        request.conversation_id, user_id, limit=50
                    )
                )
                if not existing_conversation:
                    # User doesn't own this conversation, create new one
                    logger.warning(
                        "User attempted to access conversation they don't own"
                    )
                    conversation = await self.db_service.create_conversation(
                        user_id=user_id,
                        game_name=request.game,
                        game_version=request.version,
                        user_query=request.query,
                    )
                else:
                    conversation = existing_conversation
            else:
                # Create new conversation
                conversation = await self.db_service.create_conversation(
                    user_id=user_id,
                    game_name=request.game,
                    game_version=request.version,
                    user_query=request.query,
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
                # Use stored conversation history (exclude system messages)  
                messages = await self.db_service.get_conversation_messages(
                    cast(UUID, conversation.id),  # Cast Column[UUID] to UUID for mypy
                    user_id,
                    limit=50,
                )
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                    if msg.role != "system"
                ]

            # Call Perplexity API
            response = perplexity_client.gaming_search(
                query=request.query,
                game=request.game,
                conversation_history=conversation_history,
                version=request.version,
            )

            # Extract response data
            choice = response.choices[0]
            assistant_content = choice.message.content

            # Parse search results
            search_results = []
            search_results_data = None
            if hasattr(response, "search_results") and response.search_results:
                search_results = [
                    SearchResult(
                        title=result.title,
                        url=result.url,
                        date=getattr(result, "date", None),
                    )
                    for result in response.search_results
                ]
                # Store search results as JSON for database
                search_results_data = [
                    {
                        "title": result.title,
                        "url": result.url,
                        "date": getattr(result, "date", None),
                    }
                    for result in response.search_results
                ]

            # Parse usage statistics
            usage_stats = None
            usage_stats_data = None
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
                # Store usage stats as JSON for database
                usage_stats_data = {
                    "prompt_tokens": usage_data.prompt_tokens,
                    "completion_tokens": usage_data.completion_tokens,
                    "total_tokens": usage_data.total_tokens,
                    "search_context_size": getattr(
                        usage_data, "search_context_size", None
                    ),
                    "citation_tokens": getattr(usage_data, "citation_tokens", None),
                    "num_search_queries": getattr(
                        usage_data, "num_search_queries", None
                    ),
                }

            # Store user message in database
            await self.db_service.add_message(
                conversation_id=cast(UUID, conversation.id),
                user_id=user_id,
                role="user",
                content=request.query,
            )

            # Store assistant response in database
            await self.db_service.add_message(
                conversation_id=cast(UUID, conversation.id),
                user_id=user_id,
                role="assistant",
                content=assistant_content,
                search_results=search_results_data,
                usage_stats=usage_stats_data,
                model_info={
                    "model": response.model,
                    "finish_reason": getattr(choice, "finish_reason", None),
                },
            )

            return GamingSearchResponse(
                id=response.id,
                conversation_id=cast(UUID, conversation.id),
                model=response.model,
                created=response.created,
                content=assistant_content,
                search_results=search_results,
                usage=usage_stats,
                finish_reason=getattr(choice, "finish_reason", None),
            )

        except Exception as e:
            logger.error(f"Gaming search failed: {e}")
            raise RuntimeError(f"Gaming search failed: {e!s}") from e

    async def get_conversation_history(
        self, conversation_id: UUID, user_id: UUID
    ) -> list[ConversationMessage]:
        """
        Get conversation history.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security)

        Returns:
            list[ConversationMessage]: Conversation messages
        """
        return await self.db_service.get_conversation_messages(
            conversation_id, user_id, limit=100
        )

    async def get_user_conversations(
        self, user_id: UUID, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Get user's conversations.

        Args:
            user_id: User ID
            limit: Maximum number of conversations to return

        Returns:
            list[dict]: List of conversation summaries
        """
        conversations = await self.db_service.get_user_conversations(
            user_id, limit=limit
        )

        return [
            {
                "id": str(conv.id),
                "title": conv.title,
                "game_name": conv.game_name,
                "game_version": conv.game_version,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv in conversations
        ]

    async def archive_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """
        Archive a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security)

        Returns:
            bool: True if archived successfully
        """
        return await self.db_service.archive_conversation(conversation_id, user_id)

    async def update_conversation_title(
        self, conversation_id: UUID, user_id: UUID, title: str
    ) -> bool:
        """
        Update conversation title.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security)
            title: New title

        Returns:
            bool: True if updated successfully
        """
        conversation = await self.db_service.update_conversation_title(
            conversation_id, user_id, title
        )
        return conversation is not None

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """
        Permanently delete a conversation and all its messages.

        ⚠️ WARNING: This is irreversible!

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security)

        Returns:
            bool: True if deleted successfully
        """
        return await self.db_service.delete_conversation(conversation_id, user_id)


# Note: Service instances will now be created per request with database session
# See updated routes for usage
