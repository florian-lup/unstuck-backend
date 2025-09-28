"""Gaming Lore API routes with database-backed authentication."""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.rate_limit import RateLimited
from database.connection import get_db_session
from database.service import DatabaseService
from schemas.auth import AuthenticatedUser
from schemas.gaming_lore import (
    GamingLoreRequest,
    GamingLoreResponse,
)
from services.gaming_lore_service import GamingLoreService

router = APIRouter()


@router.post("/lore", response_model=GamingLoreResponse)
async def gaming_lore(
    request_data: GamingLoreRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> GamingLoreResponse:
    """
    Perform authenticated Gaming Lore query with automatic conversation management.

    Provides detailed gaming lore, story, character, and world-building information
    using OpenAI Responses API with built-in conversation management and web search.
    OpenAI automatically handles conversation state - no manual history management needed.
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
        service = GamingLoreService(db_session)

        # Perform lore search with user authentication
        return await service.search(
            request=request_data,
            user_id=cast(UUID, internal_user.id),
            auth0_user_id=current_user.user_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "lore_search_failed",
                "message": f"Gaming Lore search failed: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


# Conversation management is handled by /api/v1/gaming/conversations
# This keeps all conversation APIs unified regardless of the feature that created them
