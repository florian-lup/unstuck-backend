"""Gaming search API routes with authentication."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.auth import get_current_user, get_optional_user
from core.rate_limit import RateLimited
from schemas.auth import AuthenticatedUser
from schemas.gaming_search import (
    ConversationHistoryResponse,
    GamingSearchRequest,
    GamingSearchResponse,
)
from services.gaming_search_service import gaming_search_service

router = APIRouter()


@router.post("/search", response_model=GamingSearchResponse)
async def gaming_search(
    request_data: GamingSearchRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> GamingSearchResponse:
    """
    Perform authenticated gaming search.

    Searches for gaming-related information using AI with conversation context.
    Requires authentication via Auth0 JWT token.
    """
    try:
        # Store user ID in request state for rate limiting
        request.state.user_id = current_user.user_id

        # Perform search using existing service
        return gaming_search_service.search(request_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "search_failed",
                "message": f"Gaming search failed: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ConversationHistoryResponse,
)
async def get_conversation_history(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> ConversationHistoryResponse:
    """
    Get conversation history for a specific conversation.

    Returns all messages in the conversation with metadata.
    """
    try:
        # Get conversation history
        messages = gaming_search_service.get_conversation_history(conversation_id)

        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "conversation_not_found",
                    "message": f"Conversation {conversation_id} not found",
                },
            )

        # Get conversation metadata (you might want to store this in the service)
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            created_at=int(conversation_id.time),  # Use UUID timestamp as creation time
            updated_at=int(
                conversation_id.time
            ),  # Simplified - you might want to track this properly
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "history_retrieval_failed",
                "message": f"Failed to retrieve conversation history: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, str | bool]:
    """
    Clear/delete a conversation.

    Removes all messages and metadata for the specified conversation.
    """
    try:
        success = gaming_search_service.clear_conversation(conversation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "conversation_not_found",
                    "message": f"Conversation {conversation_id} not found",
                },
            )

        return {
            "success": True,
            "message": f"Conversation {conversation_id} cleared successfully",
            "conversation_id": str(conversation_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "conversation_clear_failed",
                "message": f"Failed to clear conversation: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.get("/conversations")
async def list_conversations(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, list[str]]:
    """
    List all active conversations for the current user.

    Returns list of conversation IDs.
    """
    try:
        conversations = gaming_search_service.list_conversations()

        return {
            "conversations": [str(conv_id) for conv_id in conversations],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "conversation_list_failed",
                "message": f"Failed to list conversations: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


# Optional: Public search endpoint with different rate limits
@router.post("/search/public", response_model=GamingSearchResponse)
async def public_gaming_search(
    request_data: GamingSearchRequest,
    request: Request,
    current_user: AuthenticatedUser | None = Depends(get_optional_user),  # noqa: B008
) -> GamingSearchResponse:
    """
    Public gaming search endpoint with optional authentication.

    Allows unauthenticated users to perform searches with stricter rate limits.
    Authenticated users get higher rate limits and conversation persistence.
    """
    try:
        # Apply different rate limits for authenticated vs unauthenticated users
        if current_user:
            request.state.user_id = current_user.user_id

        # For unauthenticated users, don't persist conversations
        if not current_user:
            request_data.conversation_id = None

        return gaming_search_service.search(request_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "search_failed",
                "message": f"Gaming search failed: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e
