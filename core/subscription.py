"""Subscription tier checking utilities."""

from datetime import UTC, datetime
from typing import cast

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.constants import SUBSCRIPTION_LIMITS, SubscriptionTier
from database.connection import get_db_session
from database.models import User
from database.service import DatabaseService
from schemas.auth import AuthenticatedUser


async def require_community_subscription(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> AuthenticatedUser:
    """
    Dependency that requires the user to have an active Community subscription.

    Raises:
        HTTPException: If user does not have Community subscription

    Returns:
        AuthenticatedUser: The authenticated user with Community subscription

    Usage:
        @router.get("/community-feature")
        async def community_only_feature(
            user: AuthenticatedUser = Depends(require_community_subscription)
        ):
            # This endpoint is only accessible to Community users
            return {"feature": "community-only"}
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    # Check subscription tier
    if user.subscription_tier != "community":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Community subscription",
        )

    return current_user


async def get_user_subscription_tier(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> str:
    """
    Get the current user's subscription tier.

    Returns:
        str: The subscription tier ("free" or "community")

    Usage:
        @router.get("/feature")
        async def feature(
            tier: str = Depends(get_user_subscription_tier)
        ):
            if tier == "community":
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


def _check_request_limit(user: User) -> None:
    """
    Check if user has exceeded their request limit.

    Args:
        user: User database record

    Raises:
        HTTPException: If user has exceeded request limit
    """
    tier = user.subscription_tier

    if tier == "free":
        # Free tier: Check lifetime limit
        max_requests = cast(
            int, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE]["max_total_requests"]
        )
        if user.total_requests >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "request_limit_exceeded",
                    "message": (
                        f"You've used all **{max_requests} gaming chat requests** on the **{tier} tier**.\n\n"
                        "✨ **Upgrade to Community tier to continue chatting:**\n"
                        "• 300 gaming chat requests per month\n"
                        "• Monthly limit resets automatically\n"
                        "• Support development of Unstuck\n\n"
                        '💡 *Click the settings icon and select "Upgrade Subscription" to continue!*'
                    ),
                    "current_requests": user.total_requests,
                    "max_requests": max_requests,
                    "tier": tier,
                    "limit_type": "lifetime",
                    "upgrade_required": True,
                },
            )
    elif tier == "community":
        # Community tier: Check monthly limit
        max_monthly = cast(
            int, SUBSCRIPTION_LIMITS[SubscriptionTier.COMMUNITY]["max_monthly_requests"]
        )

        # Check if we need to reset monthly counter
        current_time = datetime.now(UTC)
        if user.request_count_reset_date is None:
            # First request, will be reset in increment_user_requests
            pass
        else:
            days_since_reset = (current_time - user.request_count_reset_date).days
            if days_since_reset >= 30:
                # Counter will be reset in increment_user_requests
                pass
            elif user.monthly_requests >= max_monthly:
                # Exceeded monthly limit
                days_until_reset = 30 - days_since_reset
                reset_date_str = (
                    user.request_count_reset_date.strftime("%B %d, %Y")
                    if user.request_count_reset_date
                    else "soon"
                )
                day_text = "day" if days_until_reset == 1 else "days"

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "monthly_request_limit_exceeded",
                        "message": (
                            f"You've used all **{max_monthly} gaming chat requests** this month on the **{tier} tier**.\n\n"
                            f"⏰ Your limit will reset in **{days_until_reset} {day_text}** (on {reset_date_str}).\n\n"
                            "✨ **Or upgrade to Pro tier for unlimited gaming chat:**\n"
                            "• Unlimited requests every month\n"
                            "• Exclusive features (coming soon)"
                        ),
                        "current_requests": user.monthly_requests,
                        "max_requests": max_monthly,
                        "tier": tier,
                        "limit_type": "monthly",
                        "days_until_reset": days_until_reset,
                        "reset_date": user.request_count_reset_date.isoformat()
                        if user.request_count_reset_date
                        else None,
                    },
                )


def get_request_limit_info(user: User) -> dict[str, int | str | None]:
    """
    Get request limit information for a user.

    Args:
        user: User database record

    Returns:
        dict: Dictionary containing remaining_requests, max_requests, limit_type, and reset_date
    """
    tier = user.subscription_tier

    if tier == "free":
        max_requests = cast(
            int, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE]["max_total_requests"]
        )
        remaining = max(0, max_requests - user.total_requests)
        return {
            "remaining_requests": remaining,
            "max_requests": max_requests,
            "limit_type": "lifetime",
            "reset_date": None,
        }
    if tier == "community":
        max_monthly = cast(
            int, SUBSCRIPTION_LIMITS[SubscriptionTier.COMMUNITY]["max_monthly_requests"]
        )

        # Check if monthly counter needs reset
        current_time = datetime.now(UTC)
        if user.request_count_reset_date is None:
            # First request, will be initialized
            remaining = max_monthly
            reset_date = None
        else:
            days_since_reset = (current_time - user.request_count_reset_date).days
            if days_since_reset >= 30:
                # Will be reset on next request
                remaining = max_monthly
                reset_date = current_time.isoformat()
            else:
                remaining = max(0, max_monthly - user.monthly_requests)
                # Calculate next reset date (30 days from last reset)
                next_reset = user.request_count_reset_date.replace(
                    day=user.request_count_reset_date.day
                )
                # Add 30 days
                import calendar

                year = next_reset.year
                month = next_reset.month + 1
                if month > 12:
                    month = 1
                    year += 1
                # Handle day overflow
                max_day = calendar.monthrange(year, month)[1]
                day = min(next_reset.day, max_day)
                from datetime import datetime as dt

                next_reset = dt(
                    year,
                    month,
                    day,
                    next_reset.hour,
                    next_reset.minute,
                    next_reset.second,
                    tzinfo=next_reset.tzinfo,
                )
                reset_date = next_reset.isoformat()

        return {
            "remaining_requests": remaining,
            "max_requests": max_monthly,
            "limit_type": "monthly",
            "reset_date": reset_date,
        }
    # Unknown tier or premium tier with unlimited requests
    return {
        "remaining_requests": 999999,
        "max_requests": 999999,
        "limit_type": "unlimited",
        "reset_date": None,
    }


async def check_request_limits_only(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> User:
    """
    Check GAMING CHAT request limits only (no feature restrictions) and increment counter.

    Use this for features that are available to all tiers but still count towards limits.

    Args:
        current_user: Authenticated user from JWT token
        db_session: Database session

    Returns:
        User: The user database record after incrementing request counter

    Raises:
        HTTPException: If user has exceeded request limits
    """
    # Get user from database
    db_service = DatabaseService(db_session)
    user = await db_service.get_or_create_user(
        auth0_user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.name,
    )

    # Check request limits
    _check_request_limit(user)

    # Increment request counter
    return await db_service.increment_user_requests(user.id)
