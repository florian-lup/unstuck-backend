"""Authentication and user management routes."""

import time

from fastapi import APIRouter, Depends, Request

from core.auth import get_current_user
from core.rate_limit import RateLimited
from schemas.auth import AuthenticatedUser, UserInfoResponse
from services.gaming_search_service import gaming_search_service

router = APIRouter()


@router.get("/me", response_model=UserInfoResponse)  # type: ignore[misc]
async def get_user_info(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> UserInfoResponse:
    """
    Get current user information.

    Returns user details and usage statistics.
    """
    # Get user's conversation count
    conversations = gaming_search_service.list_conversations()
    conversation_count = len(conversations)

    return UserInfoResponse(
        user=current_user,
        conversation_count=conversation_count,
        last_activity=int(time.time()),
    )


@router.post("/verify")  # type: ignore[misc]
async def verify_token(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, str | bool]:
    """
    Verify JWT token validity.

    Returns token validation status.
    """
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "message": "Token is valid",
    }


@router.get("/permissions")  # type: ignore[misc]
async def get_user_permissions(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, list[str]]:
    """
    Get current user permissions.

    Returns list of user permissions and scopes.
    """
    return {
        "permissions": current_user.permissions,
    }
