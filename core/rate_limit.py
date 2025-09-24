"""Simple in-memory rate limiting middleware."""

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from core.config import settings


class InMemoryRateLimitService:
    """Simple in-memory rate limiting service using sliding window."""

    def __init__(self) -> None:
        """Initialize rate limiting service."""
        # Store request timestamps for each key
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def is_rate_limited(
        self, key: str, limit: int | None = None, window: int | None = None
    ) -> tuple[bool, int, int]:
        """
        Check if key is rate limited using sliding window.

        Returns:
            (is_limited, current_count, time_until_reset)
        """
        if limit is None:
            limit = settings.rate_limit_requests
        if window is None:
            window = settings.rate_limit_window

        current_time = time.time()
        cutoff_time = current_time - window

        # Get the deque for this key
        requests = self._requests[key]

        # Remove expired entries
        while requests and requests[0] <= cutoff_time:
            requests.popleft()

        # Check if rate limited
        current_count = len(requests)
        if current_count >= limit:
            # Calculate time until the oldest entry expires
            if requests:
                oldest_time = requests[0]
                time_until_reset = int(window - (current_time - oldest_time)) + 1
                return True, current_count, max(time_until_reset, 0)
            return True, current_count, window

        # Add current request
        requests.append(current_time)

        return False, current_count + 1, 0


# Global rate limit service
rate_limit_service = InMemoryRateLimitService()


def get_rate_limit_key(request: Request) -> str:
    """Generate rate limit key from request."""
    # Try to get user ID from auth first
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"rate_limit:user:{user_id}"

    # Fall back to IP address
    client_ip = request.client.host if request.client else "unknown"
    return f"rate_limit:ip:{client_ip}"


async def check_rate_limit(request: Request) -> None:
    """Check rate limit for request."""
    key = get_rate_limit_key(request)

    is_limited, current_count, time_until_reset = rate_limit_service.is_rate_limited(
        key
    )

    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded. Try again in {time_until_reset} seconds.",
                "current_requests": current_count,
                "limit": settings.rate_limit_requests,
                "window_seconds": settings.rate_limit_window,
                "retry_after": time_until_reset,
            },
            headers={"Retry-After": str(time_until_reset)},
        )

    # Add rate limit headers to response
    request.state.rate_limit_current = current_count
    request.state.rate_limit_limit = settings.rate_limit_requests
    request.state.rate_limit_window = settings.rate_limit_window


# Dependency for rate limiting
RateLimited = Annotated[None, Depends(check_rate_limit)]
