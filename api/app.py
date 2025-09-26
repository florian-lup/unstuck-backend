"""FastAPI application setup with security middleware."""

import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from api.routes import auth as auth_routes
from api.routes import gaming_search as gaming_routes
from api.routes import health as health_routes
from core.config import settings
from schemas.auth import AuthError


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan context manager."""
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.version}")
    print("🔒 Authentication configured")

    # Initialize database
    try:
        from database.connection import init_database

        await init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

    yield

    # Shutdown
    try:
        from database.connection import close_database

        await close_database()
        print("✅ Database connections closed")
    except Exception as e:
        print(f"⚠️ Error closing database: {e}")

    print("🛑 Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        description="A conversational AI gaming search engine with Auth0 authentication",
        version=settings.version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Security Headers Middleware
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add security headers to responses."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), "
            "usb=(), bluetooth=(), accelerometer=(), gyroscope=(), magnetometer=()"
        )

        # Only add CSP in production
        if not settings.debug:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )

        return response

    # Request ID and timing middleware
    @app.middleware("http")
    async def request_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add request ID and timing."""
        start_time = time.time()

        # Generate request ID
        request_id = f"{int(start_time * 1000000)}"
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add timing and request ID headers
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # Add rate limit headers if available
        if hasattr(request.state, "rate_limit_current"):
            response.headers["X-RateLimit-Remaining"] = str(
                request.state.rate_limit_limit - request.state.rate_limit_current
            )
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Reset"] = str(
                int(time.time()) + request.state.rate_limit_window
            )

        return response

    # Trusted Host Middleware (security)
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "localhost",
                "127.0.0.1",
                "*.railway.app",
                "*.up.railway.app",
            ],
        )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
        expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Remaining"],
    )

    # Rate limiting handled by Redis-based middleware in dependencies

    # Global exception handlers
    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        """Handle authentication errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error,
                "description": exc.description,
                "request_id": getattr(request.state, "request_id", None),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_error",
                "description": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle internal server errors."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "description": "An internal server error occurred",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # Include routers
    app.include_router(health_routes.router, prefix="/api/v1", tags=["Health"])
    app.include_router(
        auth_routes.router, prefix="/api/v1/auth", tags=["Authentication"]
    )
    app.include_router(
        gaming_routes.router, prefix="/api/v1/gaming", tags=["Gaming Search"]
    )

    return app


# Create the app instance
app = create_app()
