"""Custom exceptions for the application."""

from typing import Any


class UnstuckError(Exception):
    """Base exception for Unstuck Backend."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(UnstuckError):
    """Raised when data validation fails."""


class AuthenticationError(UnstuckError):
    """Raised when authentication fails."""


class AuthorizationError(UnstuckError):
    """Raised when user lacks permissions."""


class ExternalAPIError(UnstuckError):
    """Raised when external API calls fail."""
    
    def __init__(self, service: str, message: str, status_code: int | None = None):
        self.service = service
        self.status_code = status_code
        details = {"service": service}
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)


class PerplexityAPIError(ExternalAPIError):
    """Raised when Perplexity AI API calls fail."""
    
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__("Perplexity AI", message, status_code)


class DatabaseError(UnstuckError):
    """Raised when database operations fail."""


class NotFoundError(UnstuckError):
    """Raised when a requested resource is not found."""
