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
        model: str,
        search_context_size: str,
        **kwargs: Any,
    ) -> Any:
        """
        Create a chat completion using Perplexity API.

        Args:
            messages: List of conversation messages
            model: The model to use
            search_context_size: Context size for web search ("low", "medium", "high")
            **kwargs: Additional parameters for the API

        Returns:
            Chat completion response
        """
        web_search_options = {"search_context_size": search_context_size}

        params = {
            "model": model,
            "messages": messages,
            "web_search_options": web_search_options,
            **kwargs,
        }

        return self._client.chat.completions.create(**params)

    def gaming_chat(
        self,
        query: str,
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        model: str = "sonar",
        search_context_size: str = "low",
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming-specific search query.

        Args:
            query: The search query about gaming
            game: The specific game name to provide context for (required)
            conversation_history: Previous messages in the conversation
            version: The game version to provide context for (optional)
            model: The model to use (default: "sonar")
            search_context_size: Context size for web search ("low", "medium", "high", default: "low")
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming information
        """
        # Build the message history
        messages = []

        # Build system prompt with integrated game context
        context_parts = [f"Game: {game}"]
        if version:
            context_parts.append(f"Version: {version}")

        system_prompt = (
            # Persona and objective
            "You are a precise, helpful gaming assistant.\n"
            "Always perform retrieval in English, but respond in the user's language and language of the user query.\n"
            "Your goal is to provide accurate, current information strictly scoped to the specified game.\n\n"
            # Scope and constraints
            "MANDATORY GAME CONTEXT (must adhere):\n"
            f"{' | '.join(context_parts)}\n\n"
            "CRITICAL CONSTRAINTS:\n"
            f"- SCOPE: Only answer about {game}{f' version {version}' if version else ''}.\n"
            f"- If no {game} information is found, reply exactly: 'No {game} information found'.\n"
            "- Prefer recent, reputable sources; avoid speculation. If uncertain, say so concisely.\n"
            "- Some search results might include coordinates, build links, talent import links, etc. You should include these in your response.\n"
            # Style and output format
            "STYLE:\n"
            "- Be concise and actionable, but don't omit important information.\n"
            "- Maintain a trashtalking tone and a cheeky attitude; use slang when appropriate and roast the user occasionally.\n\n"
            "FORMATTING RULES:\n"
            "- NEVER create tables, charts, or comparison tables\n"
            "- Use clear markdown formatting with headers (##, ###) to organize sections\n"
            "- Use numbered lists (1., 2., 3.) for step-by-step instructions and sequential processes\n"
            "- Use bullet points (-) for non-sequential information\n"
            "- Use **bold text** for emphasis on important steps, warnings, or key concepts\n"
            "- End with a relevant follow-up question.\n"
        )
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query (game context is already enforced in system prompt)
        messages.append({"role": "user", "content": query})

        return self.chat_completion(
            messages=messages,
            model=model,
            search_context_size=search_context_size,
            **kwargs,
        )

    def sonar_search(
        self,
        query: str,
        model: str = "sonar",
        search_context_size: str = "low",
        **kwargs: Any,
    ) -> Any:
        """
        Perform a simple, stateless web search using Perplexity Sonar.
        
        This is designed for tool/function calling scenarios where you need
        quick, current information without conversation context.
        No conversation history, no database storage - just query in, answer out.

        Args:
            query: The search query
            model: The model to use (default: "sonar")
            search_context_size: Context size for web search ("low", "medium", "high", default: "medium")
            **kwargs: Additional parameters for the API

        Returns:
            Chat completion response with search results
        """
        messages = [
            {
                "role": "user",
                "content": query,
            }
        ]

        return self.chat_completion(
            messages=messages,
            model=model,
            search_context_size=search_context_size,
            **kwargs,
        )

    def search(
        self,
        query: str | list[str],
        max_results: int = 10,
        max_tokens_per_page: int = 2048,
        **kwargs: Any,
    ) -> Any:
        """
        Perform a web search using Perplexity Search API.

        Args:
            query: Search query or list of queries for multi-query search
            max_results: Maximum number of results to return (default: 10)
            max_tokens_per_page: Content extraction limit per page (default: 1024)
            **kwargs: Additional parameters for the API

        Returns:
            Search results response
        """
        search_params = {
            "query": query,
            "max_results": max_results,
            "max_tokens_per_page": max_tokens_per_page,
            **kwargs,
        }

        return self._client.search.create(**search_params)


# Global client instance
perplexity_client = PerplexityClient()
