"""Gaming Builds API routes with database-backed authentication."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.rate_limit import RateLimited
from core.subscription import check_builds_access, get_request_limit_info
from database.connection import get_db_session
from database.models import User
from database.service import DatabaseService
from schemas.auth import AuthenticatedUser
from schemas.gaming_builds import (
    ConversationHistoryResponse,
    GamingBuildsRequest,
    GamingBuildsResponse,
)
from schemas.gaming_chat import RequestLimitInfo
from services.gaming_builds_service import GamingBuildsService

router = APIRouter()


@router.post("/builds", response_model=GamingBuildsResponse)
async def gaming_builds(
    request_data: GamingBuildsRequest,
    request: Request,
    internal_user: User = Depends(check_builds_access),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> GamingBuildsResponse:
    """
    Perform authenticated Gaming Builds search with database persistence.

    Searches for gaming builds, character optimization, loadouts, and equipment setups
    using AI with conversation context. All conversations and messages are stored
    securely in the database. Requires authentication via Auth0 JWT token.

    Access Requirements:
    - This feature is restricted to premium tier users
    - Free and Community tier users will receive a 403 error
    - This endpoint does NOT count towards chat request limits
    """
    try:
        # User access already checked by check_builds_access dependency
        # Note: This endpoint does NOT increment request counters
        # Store user ID in request state for rate limiting
        request.state.user_id = internal_user.auth0_user_id

        # Create service instance with database session
        service = GamingBuildsService(db_session)

        # Get request limit information
        limit_info = get_request_limit_info(internal_user)
        request_limit_info = RequestLimitInfo(
            remaining_requests=limit_info["remaining_requests"],  # type: ignore
            max_requests=limit_info["max_requests"],  # type: ignore
            limit_type=limit_info["limit_type"],  # type: ignore
            reset_date=limit_info["reset_date"],  # type: ignore
        )

        # Perform search with user authentication
        return await service.search(
            request=request_data,
            user_id=internal_user.id,
            auth0_user_id=internal_user.auth0_user_id,
            request_limit_info=request_limit_info,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "builds_search_failed",
                "message": f"Gaming Builds search failed: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.get("/conversations")
async def list_builds_conversations(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    limit: int = 20,
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    List all builds conversations for the current user.

    Returns conversations from gaming builds feature only.
    Each conversation includes a 'conversation_type' field set to 'builds'.
    """
    try:
        # Get internal user record (creates if doesn't exist)
        db_service = DatabaseService(db_session)
        internal_user = await db_service.get_or_create_user(
            auth0_user_id=current_user.user_id,
            email=current_user.email,
            username=current_user.name,
        )

        service = GamingBuildsService(db_session)

        conversations = await service.get_user_conversations(
            user_id=internal_user.id, limit=limit
        )

        return {"conversations": conversations, "total": len(conversations)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "builds_conversation_list_failed",
                "message": f"Failed to list builds conversations: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=ConversationHistoryResponse,
)
async def get_builds_conversation_history(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> ConversationHistoryResponse:
    """
    Get builds conversation history.

    Returns all messages in the builds conversation with metadata.
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

        service = GamingBuildsService(db_session)

        # Get conversation messages (includes security check)
        messages = await service.get_conversation_history(
            conversation_id=conversation_id, user_id=internal_user.id
        )

        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "builds_conversation_not_found",
                    "message": f"Builds conversation {conversation_id} not found or access denied",
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
                "error": "builds_history_retrieval_failed",
                "message": f"Failed to retrieve builds conversation history: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.put("/conversations/{conversation_id}/title")
async def update_builds_conversation_title(
    conversation_id: UUID,
    title_data: dict[str, str],
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Update builds conversation title.

    Allows users to rename their builds conversations for better organization.
    Security: Users can only update conversations they own.
    """
    try:
        service = GamingBuildsService(db_session)

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
            user_id=internal_user.id,
            title=new_title,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "builds_conversation_not_found",
                    "message": f"Builds conversation {conversation_id} not found or access denied",
                },
            )

        return {
            "success": True,
            "message": "Builds conversation title updated successfully",
            "conversation_id": str(conversation_id),
            "new_title": new_title,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "builds_title_update_failed",
                "message": f"Failed to update builds conversation title: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.post("/conversations/{conversation_id}/archive")
async def archive_builds_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Archive a builds conversation.

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

        service = GamingBuildsService(db_session)

        success = await service.archive_conversation(
            conversation_id=conversation_id, user_id=internal_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "builds_conversation_not_found",
                    "message": f"Builds conversation {conversation_id} not found or access denied",
                },
            )

        return {
            "success": True,
            "message": "Builds conversation archived successfully",
            "conversation_id": str(conversation_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "builds_archive_failed",
                "message": f"Failed to archive builds conversation: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.delete("/conversations/{conversation_id}")
async def delete_builds_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Permanently delete a builds conversation and all its messages.

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

        service = GamingBuildsService(db_session)

        success = await service.delete_conversation(
            conversation_id=conversation_id, user_id=internal_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "builds_conversation_not_found",
                    "message": f"Builds conversation {conversation_id} not found or access denied",
                },
            )

        return {
            "success": True,
            "message": "Builds conversation and all messages permanently deleted",
            "conversation_id": str(conversation_id),
            "warning": "This action was irreversible",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "builds_delete_failed",
                "message": f"Failed to delete builds conversation: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e
