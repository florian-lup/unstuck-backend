"""Health check and system status routes."""

import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.rate_limit import RateLimited
from database.connection import check_database_health, get_db_session
from schemas.auth import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
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


@router.get("/health/detailed")
async def detailed_health_check(request: Request) -> dict[str, Any]:
    """
    Detailed health check with system information.

    Only available in debug mode.
    """
    if not settings.debug:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "description": "Endpoint not available"},
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


@router.get("/health/ready")
async def readiness_check(
    _: RateLimited = None,
    db_session: AsyncSession = Depends(get_db_session)  # noqa: B008
) -> dict[str, Any]:
    """
    Kubernetes/Docker readiness probe.

    Returns 200 when the service is ready to accept traffic.
    Includes database connectivity check.
    """
    # Check database health
    db_health = await check_database_health()
    
    if db_health["status"] != "healthy":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "database": db_health,
                "message": "Database is not available"
            }
        )
    
    return {
        "status": "ready",
        "database": db_health,
        "timestamp": int(time.time())
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes/Docker liveness probe.

    Returns 200 when the service is alive.
    """
    return {"status": "alive"}
