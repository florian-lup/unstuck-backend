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
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming-specific search query.

        Args:
            query: The search query about gaming
            game: The specific game name to provide context for (required)
            conversation_history: Previous messages in the conversation
            version: The game version to provide context for (optional)
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming information
        """
        # Build the message history
        messages = []

        # Build system prompt with game context
        system_prompt_parts = []

        # Add game-specific context (game is always provided)
        context_parts = [f"Game: {game}"]
        if version:
            context_parts.append(f"Version: {version}")

        game_context = (
            f"MANDATORY GAME CONTEXT - MUST BE FOLLOWED:\n"
            f"{' | '.join(context_parts)}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"- You MUST ONLY search and provide information about {game}{f' version {version}' if version else ''}\n"
            f"- IGNORE all results about other games\n"
            f"- If no {game} information is found, explicitly state 'No {game} information found'\n"
            f"- DO NOT provide information about any other game, even if more results exist\n"
            f"- When searching, focus specifically on {game} content only\n\n"
            f"GAME SCOPE: This query is EXCLUSIVELY about {game}{f' version {version}' if version else ''}.\n"
            f"All answers must be relevant to this specific game only.\n\n"
        )
        system_prompt_parts.append(game_context)

        # Add main instructions
        main_instructions = (
            "Provide detailed, accurate gaming information from your search results only. "
            "If you cannot find reliable sources for specific information, clearly state "
            "what information could not be verified rather than speculating. "
            "Focus on factual, up-to-date information from your search results.\n\n"
            "FORMATTING RULES:\n"
            "- NEVER create tables, charts, or comparison tables\n"
            "- Use clear markdown formatting with headers (##, ###) to organize information\n"
            "- Use bullet points (-) for lists and key points\n"
            "- Use **bold text** for emphasis on important terms or concepts\n"
            "- When comparing options, use separate sections with clear headers instead of tables\n"
            "- Structure responses with logical flow: overview → key points → specific details\n"
            "- Keep paragraphs concise and well-organized\n"
            "- Use numbered lists (1., 2., 3.) only for sequential steps or ranked items\n"
            "- End with a clear, actionable summary or follow up question when appropriate"
        )
        system_prompt_parts.append(main_instructions)

        system_prompt = "".join(system_prompt_parts)
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query with game context reinforcement
        enhanced_query = f"In {game}{f' version {version}' if version else ''}: {query}"
        messages.append({"role": "user", "content": enhanced_query})

        return self.chat_completion(
            messages=messages,
            **kwargs,
        )


# Global client instance
perplexity_client = PerplexityClient()
