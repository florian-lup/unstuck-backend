"""Perplexity API client module."""

from typing import Any

from perplexity import Perplexity

from core.config import settings


class PerplexityClient:
    """Client for interacting with Perplexity API."""

    def __init__(self) -> None:
        """Initialize the Perplexity client."""
        # API key is now required by Pydantic validation, so no need for manual check
        self._client = Perplexity(api_key=settings.perplexity_api_key)

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str = "sonar",
        temperature: float = 0.2,
        search_context_size: str = "low",
        **kwargs: Any,
    ) -> Any:
        """
        Create a chat completion using Perplexity API.

        Args:
            messages: List of conversation messages
            model: The model to use (default: "sonar")
            temperature: Response randomness (0-2, default: 0.2)
            search_context_size: Context size for web search ("low", "medium", "high")
            **kwargs: Additional parameters for the API

        Returns:
            Chat completion response
        """
        web_search_options = {"search_context_size": search_context_size}

        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "web_search_options": web_search_options,
            **kwargs,
        }

        return self._client.chat.completions.create(**params)

    def gaming_search(
        self,
        query: str,
        conversation_history: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming-specific search query.

        Args:
            query: The search query about gaming
            conversation_history: Previous messages in the conversation
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming information
        """
        # Build the message history
        messages = []

        # Add system prompt for gaming context
        system_prompt = (
            "Provide detailed, accurate gaming information from your search results only."
            "If you cannot find reliable sources for specific information, clearly state "
            "what information could not be verified rather than speculating. "
            "Focus on factual, up-to-date information from your search results."
        )
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query
        messages.append({"role": "user", "content": query})

        return self.chat_completion(
            messages=messages,
            **kwargs,
        )


# Global client instance
perplexity_client = PerplexityClient()
