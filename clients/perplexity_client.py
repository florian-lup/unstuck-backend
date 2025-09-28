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

    def gaming_chat(
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

    def gaming_lore(
        self,
        query: str,
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        model: str = "sonar",
        temperature: float = 0.4,
        search_context_size: str = "low",
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming lore-specific search query.

        Args:
            query: The search query about gaming lore
            game: The specific game name to provide context for (required)
            conversation_history: Previous messages in the conversation
            version: The game version to provide context for (optional)
            model: The model to use (default: "sonar")
            temperature: Response creativity (0-2, default: 0.4 for more creative lore responses)
            search_context_size: Context size for web search ("low", "medium", "high", default: "medium")
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming lore information
        """
        # Build the message history
        messages = []

        # Build system prompt with game context for lore
        system_prompt_parts = []

        # Add game-specific context (game is always provided)
        context_parts = [f"Game: {game}"]
        if version:
            context_parts.append(f"Version: {version}")

        game_context = (
            f"MANDATORY GAME CONTEXT - MUST BE FOLLOWED:\n"
            f"{' | '.join(context_parts)}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"- Write the response as you would narrate a tale\n"
            f"- You MUST ONLY search and provide lore information about {game}\n"
            f"- IGNORE all results about other games\n"
            f"- If no {game} lore information is found, explicitly state 'No {game} lore information found'\n"
            f"- DO NOT provide information about any other game, even if more results exist\n"
            f"- When searching, focus specifically on {game} lore, story, characters, world-building content only\n\n"
            f"LORE SCOPE: This query is EXCLUSIVELY about {game} lore and storytelling.\n"
            f"All answers must be relevant to this specific game's lore only.\n\n"
        )
        system_prompt_parts.append(game_context)

        # Add lore-specific instructions
        lore_instructions = (
            "You are a lore narrator. Tell the tale in vivid, immersive prose grounded strictly "
            "in verified, canonical sources for the specified game. Write as a flowing narrative, "
            "using atmosphere, scene, and character to convey events and meaning. Prefer showing "
            "through moments and cause-and-effect over summarizing facts. Maintain continuity with "
            "established canon; if a detail is uncertain or disputed, gracefully omit it or note the uncertainty "
            "without breaking the narrative voice.\n\n"
            "OUTPUT STYLE:\n"
            "- Do not use headings, bullet points, numbered lists, tables, or markdown scaffolding.\n"
            "- Write continuous prose in short paragraphs (approximately 5–10), with varied sentence rhythm.\n"
            "- Do not include meta commentary or disclaimers.\n"
            "- End with a resonant closing line rather than a summary list.\n\n"
            "SCOPE:\n"
            f"- Focus only on {game}'s lore and storytelling.\n\n"
            "If reliable sources are lacking for a specific detail, avoid speculation rather than inventing content."
        )
        system_prompt_parts.append(lore_instructions)

        system_prompt = "".join(system_prompt_parts)
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query with game lore context reinforcement
        enhanced_query = f"Narrate the tale of {game}: {query}"
        messages.append({"role": "user", "content": enhanced_query})

        return self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            search_context_size=search_context_size,
            **kwargs,
        )

    def search(
        self,
        query: str | list[str],
        max_results: int = 10,
        max_tokens_per_page: int = 1024,
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
