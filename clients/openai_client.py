"""OpenAI API client module with tool calling support."""

import json
from typing import Any

from openai import OpenAI

from core.config import settings
from schemas.gaming_search import SearchRequest


class OpenAIClient:
    """Client for interacting with OpenAI API with tool calling capabilities."""

    def __init__(self) -> None:
        """Initialize the OpenAI client."""
        self._client = OpenAI(api_key=settings.openai_api_key)

    def gaming_lore_chat(
        self,
        query: str,
        game: str,
        conversation_history: list[dict[str, Any]] | None = None,
        version: str | None = None,
        search_function: Any = None,
        **kwargs: Any,
    ) -> Any:
        """
        Perform a gaming lore query with tool calling for search when needed.

        Args:
            query: The gaming lore query
            game: The specific game name to provide context for (required)
            conversation_history: Previous messages in the conversation
            version: The game version to provide context for (optional)
            search_function: Function to call for searching when needed
            **kwargs: Additional parameters

        Returns:
            Chat completion response with gaming lore information
        """
        # Build the message history
        messages = []

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
- Use the search tool WHENEVER you don't have complete information about the query
- If you're uncertain about any lore details, use the search tool to verify
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
        
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add the current user query
        messages.append({"role": "user", "content": query})

        # Define the search tool for function calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_gaming_information",
                    "description": f"Search for {game} gaming information, lore, story details, characters, and world-building elements when you don't have complete information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": f"Search query focused on {game} lore, story, characters, or world-building"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of search results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        # Make the initial API call with tool calling
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
            **kwargs
        )

        # Handle tool calls if present
        if response.choices[0].message.tool_calls:
            # Add the assistant's message with tool calls to the conversation
            messages.append(response.choices[0].message)

            # Process each tool call
            for tool_call in response.choices[0].message.tool_calls:
                if tool_call.function.name == "search_gaming_information":
                    # Parse the function arguments
                    function_args = json.loads(tool_call.function.arguments)
                    search_query = function_args["query"]
                    max_results = function_args.get("max_results", 10)

                    # Enhance the search query with game context
                    enhanced_query = f"{game} {search_query}"
                    if version:
                        enhanced_query += f" version {version}"

                    # Perform the search using the provided search function
                    if search_function:
                        search_request = SearchRequest(
                            query=enhanced_query,
                            max_results=max_results
                        )
                        search_results = search_function(search_request)
                        
                        # Format search results for the model
                        search_content = f"Search results for '{search_query}':\n\n"
                        if hasattr(search_results, 'results') and search_results.results:
                            for i, result in enumerate(search_results.results, 1):
                                search_content += f"{i}. **{result.title}**\n"
                                search_content += f"   URL: {result.url}\n"
                                if result.snippet:
                                    search_content += f"   Content: {result.snippet}\n"
                                if result.date:
                                    search_content += f"   Date: {result.date}\n"
                                search_content += "\n"
                        else:
                            search_content += f"No specific results found for '{search_query}'"

                        # Add the tool result to the conversation
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": search_content
                        })

            # Make a final API call to get the response with search results
            return self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                **kwargs
            )

        return response


# Global client instance
openai_client = OpenAIClient()
