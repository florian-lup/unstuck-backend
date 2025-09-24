"""FastAPI Gaming Search Engine - Production Entry Point."""

import uvicorn

from core.config import settings

if __name__ == "__main__":
    """Run the FastAPI application."""
    uvicorn.run(
        "api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        access_log=settings.debug,
        server_header=False,  # Security: hide server info
        date_header=False,  # Security: hide date header
    )
