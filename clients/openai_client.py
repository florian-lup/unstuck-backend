"""OpenAI Responses API client module with built-in conversation management and web search."""

from typing import Any

from openai import OpenAI

from core.config import settings


class OpenAIClient:
    """Client for interacting with OpenAI Responses API with built-in conversation management."""

    def __init__(self) -> None:
        """Initialize the OpenAI client for Responses API."""
        self._client = OpenAI(api_key=settings.openai_api_key)

    def create_conversation(self) -> str:
        """Create a new conversation using OpenAI Conversations API.
        
        Returns:
            Conversation ID for subsequent calls
        """
        conversation = self._client.conversations.create()
        return conversation.id
    
    def gaming_lore_chat(
        self,
        game: str,
        query: str,
        version: str | None = None,
        conversation: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming lore query using OpenAI Responses API with built-in conversation management.

        Args:
            game: The specific game name to provide context for
            query: The gaming lore query
            version: The game version to provide context for (optional)
            conversation: Optional conversation ID from create_conversation()
            **kwargs: Additional parameters

        Returns:
            Response with gaming lore information
        """
        # Build system prompt for gaming lore
        game_context = f"Game: {game}"
        if version:
            game_context += f" | Version: {version}"

        system_prompt = f"""
GAMING LORE EXPERT - CONTEXT: {game_context}

You are a gaming lore specialist focused exclusively on {game}{f' version {version}' if version else ''}. Your role is to provide detailed, accurate information about:

- Story, narrative, and plot details
- Character backgrounds, relationships, and development
- World-building, locations, and environments  
- Game history, timeline, and chronology
- Easter eggs, references, and hidden lore
- Developer commentary and behind-the-scenes information
- Community theories and interpretations (when well-founded)

CRITICAL INSTRUCTIONS:
- ONLY provide information about {game}{f' version {version}' if version else ''}
- Use web search WHENEVER you don't have complete information about the query
- If you're uncertain about any lore details, search to verify
- NEVER speculate or make up lore details - always search when unsure
- Focus on canonical information first, then community-accepted interpretations
- Clearly distinguish between official lore and fan theories

FORMATTING:
- Use clear markdown headers (##, ###) to organize information
- Use **bold** for important characters, locations, or concepts
- Use bullet points for lists and key details
- Provide sources when available from search results
- Structure responses logically: overview → key details → deeper lore

SCOPE: This conversation is EXCLUSIVELY about {game} lore and story elements.
"""

        # Build input with system message and user query
        input_data = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Use Responses API with built-in conversation management and web search
        api_params = {
            "model": "gpt-5-mini-2025-08-07",
            "input": input_data,
            "tools": [{"type": "web_search"}],
            **kwargs
        }
        
        # Add conversation only if provided (for continuing conversations)
        if conversation:
            api_params["conversation"] = conversation
            
        return self._client.responses.create(**api_params)



# Global client instance
openai_client = OpenAIClient()
