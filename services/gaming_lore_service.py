"""Gaming Lore service with OpenAI Responses API and built-in conversation management."""

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

logger = logging.getLogger(__name__)


class GamingLoreService:
    """
    Gaming Lore service using OpenAI Responses API with built-in conversation management and web search.
    
    Provides detailed gaming lore, story, character, and world-building information
    with automatic search integration using OpenAI's built-in web search tool.
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
            openai_conversation = None
            
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
                    # Create new OpenAI conversation
                    openai_conversation = openai_client.create_conversation()
                else:
                    conversation = existing_conversation
                    # For existing conversations, create fresh OpenAI conversation
                    # (OpenAI manages stateful conversations automatically)
                    openai_conversation = openai_client.create_conversation()
            else:
                # Create new conversation
                conversation = await self.db_service.create_conversation(
                    user_id=user_id,
                    game_name=request.game,
                    game_version=request.version,
                    user_query=request.query,
                    conversation_type="lore",
                )
                # Create new OpenAI conversation
                openai_conversation = openai_client.create_conversation()

            # Record start time for response time tracking
            start_time = time.time()

            # Call OpenAI Responses API with built-in conversation management and web search
            response = openai_client.gaming_lore_chat(
                game=request.game,
                query=request.query,
                version=request.version,
                conversation=openai_conversation,
            )

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Extract response data from OpenAI Responses API
            message_content = ""
            search_results: list[Any] = []
            sources_found: list[str] = []
            search_performed = False
            canonical_info = False
            tool_calls_made = 0
            
            try:
                # Get main response content
                if hasattr(response, 'output_text'):
                    message_content = response.output_text
                else:
                    message_content = "No response content available"
                    
                # Check for web search calls and extract sources
                if hasattr(response, 'output') and response.output:
                    for item in response.output:
                        # Check for web search calls
                        if getattr(item, 'type', None) == 'web_search_call':
                            search_performed = True
                            tool_calls_made += 1
                            
                        # Extract citations from message content
                        elif getattr(item, 'type', None) == 'message':
                            if hasattr(item, 'content') and item.content:
                                for content_item in item.content:
                                    if hasattr(content_item, 'annotations'):
                                        for annotation in content_item.annotations:
                                            if getattr(annotation, 'type', None) == 'url_citation':
                                                url = getattr(annotation, 'url', '')
                                                title = getattr(annotation, 'title', f"Source {len(sources_found) + 1}")
                                                if url:
                                                    sources_found.append(url)
                                                    search_results.append({
                                                        "title": title,
                                                        "url": url,
                                                        "snippet": "",
                                                        "date": ""
                                                    })
                
                # If search was performed, assume canonical info from web sources
                canonical_info = search_performed
                    
            except Exception as e:
                logger.warning(f"Error processing response: {e}")
                message_content = str(response) if response else "Error processing response"
                
            finish_reason = 'stop'

            # Extract usage statistics
            usage_stats = None
            if hasattr(response, 'usage') and response.usage:
                usage_stats = UsageStats(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    search_queries_performed=tool_calls_made,
                    structured_output_used=True,
                    responses_api_used=True
                )

            # Store user message in database
            user_message = await self.db_service.add_message(
                conversation_id=cast(UUID, conversation.id),
                user_id=user_id,
                role="user",
                content=request.query,
                search_results=None,
                usage_stats=None,
                model_info={"model": "user_input"},
            )

            # Store assistant response in database
            assistant_message = await self.db_service.add_message(
                conversation_id=cast(UUID, conversation.id),
                user_id=user_id,
                role="assistant",
                content=message_content,
                search_results=search_results,
                usage_stats=usage_stats.model_dump() if usage_stats else None,
                model_info={
                    "model": "gpt-5-mini-2025-08-07",
                    "temperature": 0.2,
                    "tool_calls_made": tool_calls_made,
                    "structured_output": True,
                    "responses_api": True,
                    "canonical_info": canonical_info,
                    "web_search_used": search_performed,
                    "response_time_ms": response_time_ms,
                    "finish_reason": finish_reason,
                },
            )

            # Create and return enhanced response with Responses API metadata
            return GamingLoreResponse(
                id=getattr(response, 'id', 'unknown'),
                conversation_id=cast(UUID, conversation.id),
                model="gpt-5-mini-2025-08-07",
                created=getattr(response, 'created', int(time.time())),
                content=message_content,
                search_results=None,  # Will be populated from sources_used instead
                usage=usage_stats,
                finish_reason=finish_reason,
                tool_calls_made=tool_calls_made,
                sources_used=sources_found,
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
