"""Custom exception classes for the Gaming Chat API."""


class GamingSearchError(Exception):
    """Base exception for Gaming Chat operations."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class PerplexityAPIError(GamingSearchError):
    """Exception for Perplexity API related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message, "perplexity_api_error")
        self.status_code = status_code


class ConversationNotFoundError(GamingSearchError):
    """Exception for when a conversation is not found."""

    def __init__(self, conversation_id: str) -> None:
        super().__init__(
            f"Conversation with ID {conversation_id} not found",
            "conversation_not_found",
        )
        self.conversation_id = conversation_id


class InvalidRequestError(GamingSearchError):
    """Exception for invalid requests."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "invalid_request")
