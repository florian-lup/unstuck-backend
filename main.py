#!/usr/bin/env python3
"""Gaming Search Engine - Conversational AI for Gaming."""

import sys
from uuid import uuid4

from schemas.gaming_search import GamingSearchRequest
from services.gaming_search_service import GamingSearchService


def main() -> None:
    """Main conversational gaming search."""
    print("🎮 Gaming Search Engine")
    print("Your AI assistant for everything gaming!\n")

    try:
        service = GamingSearchService()
        conversation_id = uuid4()

        # If user provided a question as argument, start with that
        if len(sys.argv) > 1:
            initial_query = " ".join(sys.argv[1:])
            print(f"Starting with: {initial_query}\n")
        else:
            initial_query = None

        # Start conversational loop
        while True:
            try:
                if initial_query:
                    # Use the provided question first
                    query = initial_query
                    initial_query = None  # Only use it once
                else:
                    # Get question from user
                    query = input(
                        "🎮 What would you like to know about gaming? "
                    ).strip()

                # Exit conditions
                if not query or query.lower() in ["quit", "exit", "bye", "q"]:
                    break

                print("🤔 Searching...")

                # Search with conversation context
                request = GamingSearchRequest(
                    query=query, conversation_id=conversation_id
                )

                response = service.search(request)

                # Show response
                print(f"\n{response.content}")

                # Show sources if available
                if response.search_results and len(response.search_results) > 0:
                    print(f"\n📚 Sources: {len(response.search_results)} found")

                # Show conversation context
                history = service.get_conversation_history(conversation_id)
                messages_count = len(history)
                if messages_count > 2:  # More than just this exchange
                    print(f"💬 Conversation: {messages_count} messages")

                print()  # Empty line for readability

            except KeyboardInterrupt:
                break

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure PERPLEXITY_API_KEY is in your .env file")
        return

    print("\nThanks for using Gaming Search! 🎮👋")


# Future FastAPI version:
# The same GamingSearchService will be used, just with web endpoints
# instead of this conversational CLI

if __name__ == "__main__":
    main()
