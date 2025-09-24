"""Health check and system status routes."""

import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.config import settings
from core.rate_limit import RateLimited
from schemas.auth import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)  # type: ignore[misc]
async def health_check(_: RateLimited = None) -> HealthResponse:
    """
    Health check endpoint.

    Returns basic service health information.
    """
    return HealthResponse(
        status="healthy",
        version=settings.version,
        timestamp=int(time.time()),
    )


@router.get("/health/detailed")  # type: ignore[misc]
async def detailed_health_check(request: Request) -> dict[str, Any]:
    """
    Detailed health check with system information.

    Only available in debug mode.
    """
    if not settings.debug:
        return JSONResponse(  # type: ignore[no-any-return]
            status_code=404,
            content={"error": "not_found", "description": "Endpoint not available"},
        )

    return {
        "status": "healthy",
        "version": settings.version,
        "timestamp": int(time.time()),
        "request_id": getattr(request.state, "request_id", None),
        "config": {
            "debug": settings.debug,
            "auth0_domain": settings.auth0_domain,
            "allowed_origins": settings.allowed_origins,
            "rate_limit": {
                "requests": settings.rate_limit_requests,
                "window": settings.rate_limit_window,
            },
        },
        "system": {
            "python_version": "3.13+",
            "fastapi_app": settings.app_name,
        },
    }


@router.get("/health/ready")  # type: ignore[misc]
async def readiness_check(_: RateLimited = None) -> dict[str, str]:
    """
    Kubernetes/Docker readiness probe.

    Returns 200 when the service is ready to accept traffic.
    """
    # Add any dependency checks here (database, Redis, etc.)
    # For now, just return ready
    return {"status": "ready"}


@router.get("/health/live")  # type: ignore[misc]
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes/Docker liveness probe.

    Returns 200 when the service is alive.
    """
    return {"status": "alive"}
