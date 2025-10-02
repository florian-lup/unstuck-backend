"""Subscription tier checking utilities."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from database.connection import get_db_session
from database.service import DatabaseService
from schemas.auth import AuthenticatedUser


async def require_pro_subscription(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthenticatedUser:
    """
    Dependency that requires the user to have an active Pro subscription.

    Raises:
        HTTPException: If user does not have Pro subscription

    Returns:
        AuthenticatedUser: The authenticated user with Pro subscription

    Usage:
        @router.get("/pro-feature")
        async def pro_only_feature(
            user: AuthenticatedUser = Depends(require_pro_subscription)
        ):
            # This endpoint is only accessible to Pro users
            return {"feature": "pro-only"}
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    # Check subscription tier
    if user.subscription_tier != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Pro subscription",
        )

    return current_user


async def get_user_subscription_tier(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> str:
    """
    Get the current user's subscription tier.

    Returns:
        str: The subscription tier ("free" or "pro")

    Usage:
        @router.get("/feature")
        async def feature(
            tier: str = Depends(get_user_subscription_tier)
        ):
            if tier == "pro":
                return {"full_results": [...]}
            else:
                return {"limited_results": [...]}
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    return user.subscription_tier

