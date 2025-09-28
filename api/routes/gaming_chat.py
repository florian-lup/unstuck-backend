"""Gaming Chat API routes with database-backed authentication."""

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.rate_limit import RateLimited
from database.connection import get_db_session
from database.service import DatabaseService
from schemas.auth import AuthenticatedUser
from schemas.gaming_chat import (
    ConversationHistoryResponse,
    GamingChatRequest,
    GamingChatResponse,
)
from services.gaming_chat_service import GamingChatService

router = APIRouter()


@router.post("/chat", response_model=GamingChatResponse)
async def gaming_chat(
    request_data: GamingChatRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> GamingChatResponse:
    """
    Perform authenticated Gaming Chat with database persistence.

    Searches for gaming-related information using AI with conversation context.
    All conversations and messages are stored securely in the database.
    Requires authentication via Auth0 JWT token.
    """
    try:
        # Store user ID in request state for rate limiting
        request.state.user_id = current_user.user_id

        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        # Create service instance with database session
        service = GamingChatService(db_session)

        # Perform search with user authentication
        return await service.search(
            request=request_data,
            user_id=cast(UUID, internal_user.id),
            auth0_user_id=current_user.user_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "search_failed",
                "message": f"Gaming Chat failed: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.get("/conversations")
async def list_conversations(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    limit: int = 20,
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    List all conversations for the current user from ALL features.

    Returns conversations from gaming chat and any future features.
    Each conversation includes a 'conversation_type' field to identify its source.
    """
    try:
        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        service = GamingChatService(db_session)

        conversations = await service.get_user_conversations(
            user_id=cast(UUID, internal_user.id), limit=limit
        )

        return {"conversations": conversations, "total": len(conversations)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "conversation_list_failed",
                "message": f"Failed to list conversations: {str(e)}",
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
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> ConversationHistoryResponse:
    """
    Get conversation history for ANY conversation (chat, etc.).

    Returns all messages in the conversation with metadata.
    Works for conversations from any feature (chat, future features).
    Security: Users can only access conversations they own.
    """
    try:
        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        service = GamingChatService(db_session)

        # Get conversation messages (includes security check)
        messages = await service.get_conversation_history(
            conversation_id=conversation_id, user_id=cast(UUID, internal_user.id)
        )

        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "conversation_not_found",
                    "message": f"Conversation {conversation_id} not found or access denied",
                },
            )

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            created_at=int(conversation_id.time),  # Use UUID timestamp as creation time
            updated_at=int(conversation_id.time),  # Simplified for now
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


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: UUID,
    title_data: dict[str, str],
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Update conversation title.

    Allows users to rename their conversations for better organization.
    Security: Users can only update conversations they own.
    """
    try:
        service = GamingChatService(db_session)

        new_title = title_data.get("title", "").strip()
        if not new_title or len(new_title) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_title",
                    "message": "Title must be between 1 and 500 characters",
                },
            )

        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        success = await service.update_conversation_title(
            conversation_id=conversation_id,
            user_id=cast(UUID, internal_user.id),
            title=new_title,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "conversation_not_found",
                    "message": f"Conversation {conversation_id} not found or access denied",
                },
            )

        return {
            "success": True,
            "message": "Conversation title updated successfully",
            "conversation_id": str(conversation_id),
            "new_title": new_title,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "title_update_failed",
                "message": f"Failed to update conversation title: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Archive a conversation.

    Archived conversations are hidden from the main list but not deleted.
    Users can still access them if they have the conversation ID.
    Security: Users can only archive conversations they own.
    """
    try:
        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        service = GamingChatService(db_session)

        success = await service.archive_conversation(
            conversation_id=conversation_id, user_id=cast(UUID, internal_user.id)
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "conversation_not_found",
                    "message": f"Conversation {conversation_id} not found or access denied",
                },
            )

        return {
            "success": True,
            "message": "Conversation archived successfully",
            "conversation_id": str(conversation_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "archive_failed",
                "message": f"Failed to archive conversation: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Permanently delete a conversation and all its messages.

    ⚠️ WARNING: This action is irreversible!

    All messages in the conversation will be permanently deleted from the database.
    Consider using the archive endpoint if you want to hide the conversation instead.

    Security: Users can only delete conversations they own.
    GDPR Compliance: Allows users to permanently remove their data.
    """
    try:
        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        service = GamingChatService(db_session)

        success = await service.delete_conversation(
            conversation_id=conversation_id, user_id=cast(UUID, internal_user.id)
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "conversation_not_found",
                    "message": f"Conversation {conversation_id} not found or access denied",
                },
            )

        return {
            "success": True,
            "message": "Conversation and all messages permanently deleted",
            "conversation_id": str(conversation_id),
            "warning": "This action was irreversible",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "delete_failed",
                "message": f"Failed to delete conversation: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e
