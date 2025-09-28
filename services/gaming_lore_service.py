"""Gaming Lore service with OpenAI GPT-4o mini and database-backed conversation management."""

import logging
import time
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from clients.openai_client import openai_client
from database.models import Conversation
from database.service import DatabaseService
from schemas.gaming_lore import (
    ConversationMessage,
    GamingLoreRequest,
    GamingLoreResponse,
    UsageStats,
)
from schemas.gaming_search import SearchRequest
from services.gaming_search_service import search_service

logger = logging.getLogger(__name__)


class GamingLoreService:
    """
    Gaming Lore service using OpenAI GPT-4o mini with tool calling for search.
    
    Provides detailed gaming lore, story, character, and world-building information
    with automatic search integration when the AI needs additional information.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize the Gaming Lore service with database session."""
        self.db_service = DatabaseService(db_session)

    async def search(
        self, request: GamingLoreRequest, user_id: UUID, auth0_user_id: str
    ) -> GamingLoreResponse:
        """
        Perform a Gaming Lore query with conversation context and tool calling.

        Args:
            request: Gaming Lore request
            user_id: User ID from database
            auth0_user_id: Auth0 user identifier

        Returns:
            Gaming Lore response with detailed information
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
                        conversation_type="lore",
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
                    conversation_type="lore",
                )

            # Build conversation history for OpenAI API
            conversation_history = []
            if request.conversation_history:
                # Use provided conversation history
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_history
                ]
            elif conversation.messages:
                # Use stored conversation history from database
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in conversation.messages[-10:]  # Last 10 messages for context
                ]

            # Create search function for tool calling
            def search_function(search_request: SearchRequest):
                """Synchronous wrapper for gaming search service."""
                try:
                    # Use the existing search service
                    import asyncio
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(search_service.search(search_request))
                except Exception as e:
                    logger.error(f"Search function failed: {str(e)}")
                    return None

            # Record start time for response time tracking
            start_time = time.time()

            # Call OpenAI with tool calling for search
            response = openai_client.gaming_lore_chat(
                query=request.query,
                game=request.game,
                version=request.version,
                conversation_history=conversation_history,
                search_function=search_function,
            )

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Extract response data
            choice = response.choices[0]
            message_content = choice.message.content
            finish_reason = choice.finish_reason

            # Extract usage statistics
            usage_stats = None
            if response.usage:
                usage_stats = UsageStats(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    search_queries_performed=len(choice.message.tool_calls or [])
                )

            # Process search results if tool calls were made
            search_results = []
            tool_calls_made = 0
            if choice.message.tool_calls:
                tool_calls_made = len(choice.message.tool_calls)
                # Note: Search results are integrated into the response content
                # We don't extract them separately as they're used internally by the model

            # Store user message in database
            await self.db_service.create_message(
                conversation_id=cast(UUID, conversation.id),
                role="user",
                content=request.query,
                search_results=None,
                usage_stats=None,
                model_info={"model": "user_input"},
                response_time_ms=None,
                finish_reason=None,
            )

            # Store assistant response in database
            await self.db_service.create_message(
                conversation_id=cast(UUID, conversation.id),
                role="assistant",
                content=message_content,
                search_results=search_results,
                usage_stats=usage_stats.model_dump() if usage_stats else None,
                model_info={
                    "model": "gpt-4o-mini",
                    "temperature": 0.2,
                    "tool_calls_made": tool_calls_made,
                },
                response_time_ms=str(response_time_ms),
                finish_reason=finish_reason,
            )

            # Create and return response
            return GamingLoreResponse(
                id=response.id,
                conversation_id=cast(UUID, conversation.id),
                model="gpt-4o-mini",
                created=response.created,
                content=message_content,
                search_results=search_results if search_results else None,
                usage=usage_stats,
                finish_reason=finish_reason,
                tool_calls_made=tool_calls_made,
            )

        except Exception as e:
            logger.error(f"Gaming Lore search failed: {str(e)}")
            raise RuntimeError(f"Gaming Lore search failed: {str(e)}") from e

    async def get_conversation_history(
        self, conversation_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """
        Get conversation history for a gaming lore conversation.

        Args:
            conversation_id: Conversation ID to retrieve
            user_id: User ID for security verification

        Returns:
            Conversation history with messages
        """
        try:
            conversation = await self.db_service.get_conversation_with_messages(
                conversation_id, user_id, limit=100
            )

            if not conversation:
                raise ValueError("Conversation not found or access denied")

            messages = [
                ConversationMessage(role=msg.role, content=msg.content)
                for msg in conversation.messages
            ]

            return {
                "conversation_id": conversation.id,
                "messages": messages,
                "created_at": int(conversation.created_at.timestamp()),
                "updated_at": int(conversation.updated_at.timestamp()),
                "game_name": conversation.game_name,
                "game_version": conversation.game_version,
            }

        except Exception as e:
            logger.error(f"Get conversation history failed: {str(e)}")
            raise RuntimeError(f"Failed to retrieve conversation history: {str(e)}") from e
