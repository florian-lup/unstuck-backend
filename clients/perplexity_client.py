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
        temperature: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Create a chat completion using Perplexity API.

        Args:
            messages: List of conversation messages
            model: The model to use
            search_context_size: Context size for web search ("low", "medium", "high")
            temperature: Response randomness (0-2, optional)
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

        # Only include temperature if provided
        if temperature is not None:
            params["temperature"] = temperature

        return self._client.chat.completions.create(**params)

    def gaming_chat(
        self,
        query: str,
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        model: str = "sonar",
        temperature: float = 0.2,
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
            temperature: Response randomness (0-2, default: 0.2)
            search_context_size: Context size for web search ("low", "medium", "high", default: "low")
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
            model=model,
            temperature=temperature,
            search_context_size=search_context_size,
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

    def gaming_guides(
        self,
        query: str,
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        model: str = "sonar-reasoning",
        search_context_size: str = "low",
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming guides-specific search query.

        Args:
            query: The search query about gaming guides/tutorials
            game: The specific game name to provide context for (required)
            conversation_history: Previous messages in the conversation
            version: The game version to provide context for (optional)
            model: The model to use (default: "sonar")
            search_context_size: Context size for web search ("low", "medium", "high", default: "high")
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming guides information
        """
        # Build the message history
        messages = []

        # Build system prompt with game context for guides
        system_prompt_parts = []

        # Add game-specific context (game is always provided)
        context_parts = [f"Game: {game}"]
        if version:
            context_parts.append(f"Version: {version}")

        game_context = (
            f"MANDATORY GAME CONTEXT - MUST BE FOLLOWED:\n"
            f"{' | '.join(context_parts)}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"- You MUST ONLY search and provide guide information about {game}{f' version {version}' if version else ''}\n"
            f"- IGNORE all results about other games\n"
            f"- If no {game} guide information is found, explicitly state 'No {game} guide information found'\n"
            f"- DO NOT provide information about any other game, even if more results exist\n"
            f"- When searching, focus specifically on {game} tutorials, guides, walkthroughs, and how-to content only\n\n"
            f"GUIDES SCOPE: This query is EXCLUSIVELY about {game}{f' version {version}' if version else ''} guides and tutorials.\n"
            f"All answers must be relevant to this specific game's guides only.\n\n"
        )
        system_prompt_parts.append(game_context)

        # Add guides-specific instructions
        guides_instructions = (
            "You are a specialist in gaming guides, tutorials, and walkthroughs. "
            "Provide detailed, step-by-step instructions, tips, strategies, and tutorials "
            "from your search results only. Focus on practical, actionable information "
            "that helps players accomplish specific goals, overcome challenges, or learn game mechanics.\n\n"
            "GUIDES FOCUS AREAS:\n"
            "- **Step-by-Step Tutorials**: Clear, numbered instructions for completing tasks\n"
            "- **Tips & Strategies**: Effective approaches, tactics, and techniques\n"
            "- **Walkthroughs**: Complete guides for levels, quests, or storylines\n"
            "- **Game Mechanics**: How systems work, controls, and gameplay features\n"
            "- **Troubleshooting**: Solutions for common problems or difficult sections\n"
            "- **Optimization**: Best practices, efficiency tips, and performance advice\n"
            "- **Builds & Loadouts**: Character builds, equipment setups, skill trees\n"
            "- **Collectibles & Secrets**: Locations of hidden items, easter eggs, achievements\n\n"
            "FORMATTING RULES:\n"
            "- NEVER create tables, charts, or comparison tables\n"
            "- Use clear markdown formatting with headers (##, ###) to organize guide sections\n"
            "- Use numbered lists (1., 2., 3.) for step-by-step instructions and sequential processes\n"
            "- Use bullet points (-) for tips, requirements, or non-sequential information\n"
            "- Use **bold text** for emphasis on important steps, warnings, or key concepts\n"
            "- Structure responses with logical flow: overview → prerequisites → detailed steps → tips\n"
            "- Include clear section breaks between different topics or procedures\n"
            "- Use > blockquotes for important warnings or critical information\n"
            "- End with helpful tips or next steps when appropriate\n\n"
            "PRECISION REQUIREMENTS:\n"
            "- Be extremely accurate with button names, menu locations, and specific instructions\n"
            "- Include exact timing, positioning, or numerical values when relevant\n"
            "- Specify difficulty levels, prerequisites, or requirements upfront\n"
            "- If multiple methods exist, present the most reliable/popular method first\n\n"
            "If you cannot find reliable guide sources for specific information, clearly state "
            "what guide information could not be verified rather than providing potentially incorrect steps."
        )
        system_prompt_parts.append(guides_instructions)

        system_prompt = "".join(system_prompt_parts)
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query with game guides context reinforcement
        enhanced_query = f"Show me how to do this in {game}{f' version {version}' if version else ''}: {query}"
        messages.append({"role": "user", "content": enhanced_query})

        return self.chat_completion(
            messages=messages,
            model=model,
            search_context_size=search_context_size,
            **kwargs,
        )

    def gaming_builds(
        self,
        query: str,
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        model: str = "sonar-reasoning",
        search_context_size: str = "low",
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming builds-specific search query.

        Args:
            query: The search query about gaming builds/loadouts
            game: The specific game name to provide context for (required)
            conversation_history: Previous messages in the conversation
            version: The game version to provide context for (optional)
            model: The model to use (default: "sonar-reasoning")
            search_context_size: Context size for web search ("low", "medium", "high", default: "low")
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming builds information
        """
        # Build the message history
        messages = []

        # Build system prompt with game context for builds
        system_prompt_parts = []

        # Add game-specific context (game is always provided)
        context_parts = [f"Game: {game}"]
        if version:
            context_parts.append(f"Version: {version}")

        game_context = (
            f"MANDATORY GAME CONTEXT - MUST BE FOLLOWED:\n"
            f"{' | '.join(context_parts)}\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"- You MUST ONLY search and provide build information about {game}{f' version {version}' if version else ''}\n"
            f"- IGNORE all results about other games\n"
            f"- If no {game} build information is found, explicitly state 'No {game} build information found'\n"
            f"- DO NOT provide information about any other game, even if more results exist\n"
            f"- When searching, focus specifically on {game} builds, loadouts, character optimization, and equipment setups only\n\n"
            f"BUILDS SCOPE: This query is EXCLUSIVELY about {game}{f' version {version}' if version else ''} builds and character optimization.\n"
            f"All answers must be relevant to this specific game's builds only.\n\n"
        )
        system_prompt_parts.append(game_context)

        # Add builds-specific instructions
        builds_instructions = (
            "You are a specialist in gaming builds, character optimization, and equipment setups. "
            "Provide detailed, optimized builds and loadouts from your search results only. "
            "Focus on effective character configurations, equipment choices, stat distributions, "
            "skill trees, and synergistic combinations that maximize performance for specific playstyles or objectives.\n\n"
            "BUILDS FOCUS AREAS:\n"
            "- **Character Builds**: Complete stat distributions, attribute allocations, level progression\n"
            "- **Equipment Loadouts**: Weapon combinations, armor sets, accessory choices\n"
            "- **Skill Trees**: Optimal skill point allocation, ability progression paths\n"
            "- **Synergies**: How different build elements work together effectively\n"
            "- **Playstyle Optimization**: Builds tailored for specific roles (DPS, tank, support, etc.)\n"
            "- **Meta Builds**: Current popular and effective build configurations\n"
            "- **Budget/Progression Builds**: Builds for different stages of game progression\n"
            "- **Situational Builds**: Specialized builds for specific encounters or content\n\n"
            "FORMATTING RULES:\n"
            "- NEVER create tables, charts, or comparison tables\n"
            "- Use clear markdown formatting with headers (##, ###) to organize build sections\n"
            "- Use bullet points (-) for equipment lists, stat requirements, or build components\n"
            "- Use **bold text** for emphasis on key items, stats, or important build elements\n"
            "- Structure responses with logical flow: build overview → core components → alternatives → tips\n"
            "- Include clear sections for different build aspects (stats, equipment, skills, etc.)\n"
            "- Use numbered lists (1., 2., 3.) for build progression steps or priority orders\n"
            "- End with build tips, variations, or upgrade paths when appropriate\n\n"
            "BUILD REQUIREMENTS:\n"
            "- Always specify minimum level requirements or prerequisites\n"
            "- Include exact stat numbers, percentages, or values when available\n"
            "- Mention alternative equipment options for different budgets or availability\n"
            "- Explain the reasoning behind key build choices and synergies\n"
            "- Include performance expectations and suitable content types for each build\n\n"
            "If you cannot find reliable build sources for specific information, clearly state "
            "what build information could not be verified rather than providing potentially suboptimal recommendations."
        )
        system_prompt_parts.append(builds_instructions)

        system_prompt = "".join(system_prompt_parts)
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query with game builds context reinforcement
        enhanced_query = f"Show me optimal builds for {game}{f' version {version}' if version else ''}: {query}"
        messages.append({"role": "user", "content": enhanced_query})

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
