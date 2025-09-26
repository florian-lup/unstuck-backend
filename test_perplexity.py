#!/usr/bin/env python3
"""Gaming Search Engine - Conversational AI for Gaming."""


# NOTE: This CLI test needs to be updated to work with the new database-backed service
# For now, use the FastAPI endpoints for testing
print("❌ This CLI test is outdated. Please use the FastAPI endpoints for testing.")
print("💡 Run: poetry run python main.py")
print("💡 Then test with: curl http://localhost:8000/api/v1/health")

def main() -> None:
    """Main conversational gaming search.""" 
    print("🎮 This test needs database setup and has been disabled.")
    print("🔧 Use the FastAPI application instead.")
    
    # OLD CODE - DISABLED FOR NOW
    # Uncomment and update after setting up database
    """
    print("🎮 Gaming Search Engine")
    print("Your AI assistant for everything gaming!\n")

    try:
        # Need to create database session first
        service = GamingSearchService(db_session)
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
                    query=query, 
                    game="World of Warcraft",  # Default game context for CLI
                    conversation_id=conversation_id
                )

                # response = await service.search(request, user_id, auth0_user_id)

                # # Show response
                # print(f"\n{response.content}")

                # # Show sources if available
                # if response.search_results and len(response.search_results) > 0:
                #     print(f"\n📚 Sources ({len(response.search_results)} found):")
                #     for i, source in enumerate(response.search_results, 1):
                #         print(f"  {i}. {source.title}")
                #         print(f"     🔗 {source.url}")
                #         if source.date:
                #             print(f"     📅 {source.date}")
                #         print()  # Empty line between sources

                # # Show conversation context
                # history = await service.get_conversation_history(conversation_id, user_id)
                # messages_count = len(history)
                # if messages_count > 2:  # More than just this exchange
                #     print(f"💬 Conversation: {messages_count} messages")

                # print()  # Empty line for readability

            except KeyboardInterrupt:
                break

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure PERPLEXITY_API_KEY is in your .env file")
        return

    print("\nThanks for using Gaming Search! 🎮👋")
    """


# Future FastAPI version:
# The same GamingSearchService will be used, just with web endpoints
# instead of this conversational CLI

if __name__ == "__main__":
    main()
