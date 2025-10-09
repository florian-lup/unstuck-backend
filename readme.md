# Gaming Chat Engine

An AI-powered Gaming Chat engine built with Perplexity AI. This tool allows users to search for gaming information using natural language queries with conversation context.

## Features

- 🎮 **Gaming-focused AI search** - Specialized prompts for gaming content
- 🎙️ **Real-time Voice Chat** - OpenAI Realtime API integration for low-latency voice interactions
- 💬 **Multi-step conversations** - Maintains conversation context across requests
- 🔍 **Advanced search filters** - Time-based filtering and search customization
- 📊 **Usage analytics** - Token usage and performance metrics
- 🚀 **Modern Python** - Built with Python 3.13 and Poetry
- 🖥️ **FastAPI Backend** - Production-ready REST API with Auth0 authentication
- 🔐 **Secure Authentication** - Auth0 JWT authentication with subscription management

## Project Structure

```
unstuck-backend/
├── api/
│   ├── app.py                   # FastAPI application setup
│   └── routes/
│       ├── auth.py              # Authentication routes
│       ├── gaming_chat.py       # Gaming chat routes
│       ├── voice_chat.py        # Voice chat routes (NEW!)
│       ├── subscription.py      # Stripe subscription routes
│       └── health.py            # Health check routes
├── clients/
│   ├── perplexity_client.py     # Perplexity API client
│   └── openai_client.py         # OpenAI Realtime API client (NEW!)
├── core/
│   ├── config.py                # Application configuration
│   ├── auth.py                  # Auth0 JWT authentication
│   ├── subscription.py          # Subscription management
│   └── rate_limit.py            # Rate limiting
├── database/
│   ├── models.py                # SQLAlchemy models
│   ├── connection.py            # Database connection
│   └── service.py               # Database service layer
├── schemas/
│   ├── gaming_chat.py           # Gaming chat schemas
│   ├── voice_chat.py            # Voice chat schemas (NEW!)
│   ├── auth.py                  # Auth schemas
│   └── subscription.py          # Subscription schemas
├── services/
│   ├── gaming_chat_service.py   # Gaming chat business logic
│   └── subscription_service.py  # Subscription service
├── docs/
│   ├── VOICE_CHAT_IMPLEMENTATION.md  # Full voice chat guide (NEW!)
│   ├── VOICE_CHAT_QUICKSTART.md      # Quick start guide (NEW!)
│   └── *.md                          # Other documentation
├── main.py                      # Application entry point
├── pyproject.toml              # Poetry configuration
└── .env.example                # Environment variables template
```

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Perplexity AI API key
- OpenAI API key (for voice chat feature)
- Auth0 account (for authentication)
- PostgreSQL database (Neon recommended)

### Installation

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd unstuck-backend
   ```

2. **Install dependencies using Poetry:**

   ```bash
   poetry install
   ```

3. **Set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env and add your Perplexity API key
   ```

4. **Get your API keys:**

   **Perplexity API:**

   - Visit the [Perplexity API Portal](https://docs.perplexity.ai/getting-started/quickstart)
   - Navigate to the **API Keys** tab and generate a new key

   **OpenAI API (for voice chat):**

   - Visit [OpenAI Platform](https://platform.openai.com/api-keys)
   - Create a new API key with Realtime API access

   **Auth0:**

   - Create account at [Auth0](https://auth0.com)
   - Set up application and API

   Add all keys to your `.env` file:

   ```
   PERPLEXITY_API_KEY=your_perplexity_key
   OPENAI_API_KEY=your_openai_key
   AUTH0_DOMAIN=your-domain.auth0.com
   AUTH0_API_AUDIENCE=your-api-audience
   DATABASE_URL=postgresql://...
   STRIPE_API_KEY=your_stripe_key
   ```

### Running the Application

1. **Start the FastAPI server:**

   ```bash
   poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Or simply:

   ```bash
   poetry run python main.py
   ```

2. **Gaming Chat testing:**

   ```bash
   # Single query test
   poetry run python test_gaming_chat.py "What are the best RPG games of 2024?"

   # Interactive mode with conversation context
   poetry run python test_gaming_chat.py --interactive

   # Test conversation context with predefined queries
   poetry run python test_gaming_chat.py --conversation

   # Show help and options
   poetry run python test_gaming_chat.py --help
   ```

3. **Validate setup:**
   ```bash
   poetry run python test_setup.py
   ```

## Usage Examples

### Single Query Testing

```bash
# Test specific gaming questions
poetry run python test_gaming_chat.py "What are the best indie games of 2024?"
poetry run python test_gaming_chat.py "Compare PS5 vs Xbox Series X performance"
poetry run python test_gaming_chat.py "Tell me about Elden Ring gameplay mechanics"
```

### Interactive Testing Mode

```bash
poetry run python test_gaming_chat.py --interactive

# Then ask questions interactively with conversation context:
🎮 Ask a gaming question (or 'quit'): Tell me about Elden Ring
🎮 Ask a gaming question (or 'quit'): What about its DLC content?
🎮 Ask a gaming question (or 'quit'): How does it compare to other FromSoftware games?
🎮 Ask a gaming question (or 'quit'): quit
```

### Conversation Context Testing

```bash
# Test predefined conversation flow to verify context works
poetry run python test_gaming_chat.py --conversation
```

## Features

### 🎯 Gaming-Optimized Search

- Specialized AI prompts for gaming content
- Comprehensive game information including platforms, release dates, and features
- Gaming hardware comparisons and recommendations
- Industry news and trends

### 🎙️ Real-time Voice Chat (NEW!)

- **OpenAI Realtime API Integration**: Ultra-low latency voice interactions (<500ms)
- **Ephemeral Tokens**: Secure token generation for direct client-to-OpenAI connections
- **8 Voice Options**: alloy, echo, shimmer, ash, ballad, coral, sage, verse
- **Game-Specific AI**: Automatically tailors assistant to your current game
- **WebSocket-based**: Direct WebSocket connection from Electron client
- **Optimized for Gaming**: Perfect for in-game voice assistance and live gameplay help

**Quick Start:**

- See [Voice Chat Quick Start Guide](docs/VOICE_CHAT_QUICKSTART.md)
- Full implementation: [Voice Chat Implementation Guide](docs/VOICE_CHAT_IMPLEMENTATION.md)
- Game examples: [Voice Chat Game Examples](docs/VOICE_CHAT_GAME_EXAMPLES.md)

**API Endpoints:**

- `POST /api/v1/voice/session` - Create ephemeral token (with optional `game` parameter)
- `GET /api/v1/voice/info` - Get available voices and info

**Example:**

```javascript
// Create game-specific voice assistant
fetch("/api/v1/voice/session", {
  body: JSON.stringify({
    voice: "alloy",
    game: "Elden Ring", // Auto-tailors AI to this game
  }),
});
```

### 💬 Conversation Context

- Maintains conversation history across multiple queries
- Follow-up questions understand previous context
- Each conversation gets a unique ID for tracking
- Full database persistence with PostgreSQL

## Configuration

Key configuration options in your `.env` file:

```bash
# Required - Perplexity AI
PERPLEXITY_API_KEY=your_perplexity_key_here

# Required - OpenAI (Voice Chat)
OPENAI_API_KEY=your_openai_key_here

# Required - Auth0
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_AUDIENCE=your-api-audience

# Required - Database
DATABASE_URL=postgresql://user:pass@host/db

# Required - Stripe
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_COMMUNITY=price_...

# Optional
DEBUG=false                  # Debug mode
SECRET_KEY=your-secret-key   # JWT secret
PORT=8000                    # Server port
```

## Search Parameters

The API supports various search parameters:

- **model**: `sonar` (default)
- **search_context_size**: `low` (default for efficiency)

### 📦 Core Dependencies

```toml
"pydantic (>=2.11.9,<3.0.0)",           # Data validation and serialization
"pydantic-settings (>=2.10.1,<3.0.0)",  # Configuration management
"perplexityai (>=0.10.0,<0.11.0)",      # Official Perplexity SDK
"openai (>=1.59.8,<2.0.0)",             # OpenAI Realtime API
"fastapi (>=0.115.0,<0.116.0)",         # Modern web framework
"sqlalchemy[asyncio] (>=2.0.25,<3.0.0)", # ORM with async support
"stripe (>=11.3.0,<12.0.0)",            # Payment processing
```

## Development

### Code Quality

The project uses modern Python tooling:

- **Ruff**: For linting and formatting
- **MyPy**: For type checking
- **Pydantic**: For data validation

Run quality checks:

```bash
poetry run ruff check .
poetry run ruff format .
poetry run mypy .
```

### Project Architecture

- **Modular Design**: Clear separation of concerns
- **Dependency Injection**: Clean service dependencies
- **Type Safety**: Full type annotations with MyPy
- **Modern Async**: Async/await throughout
- **Error Handling**: Comprehensive exception handling

## File Structure

### Application Files

- **`main.py`** - Clean application entry point and status
- **`test_gaming_chat.py`** - Comprehensive testing interface with multiple modes
- **`test_setup.py`** - Setup validation and configuration testing

### Core Architecture

- **`clients/`** - External API integrations (Perplexity)
- **`core/`** - Configuration, constants, and core exceptions
- **`schemas/`** - Pydantic models for request/response validation
- **`services/`** - Business logic and conversation management
- **`utils/`** - Utility functions and custom exceptions

## Perplexity AI Integration

This project uses the [Perplexity AI API](https://docs.perplexity.ai/) with:

- **Model**: `sonar` for balanced performance
- **Search Context**: `low` for efficient searches
- **Conversation Support**: Multi-turn conversations with full context
- **Gaming Optimization**: Specialized system prompts for gaming content

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run quality checks
6. Submit a pull request

## Support

For questions and support:

- Check the application help: `python test_gaming_chat.py --help`
- Validate your setup: `python test_setup.py`
- Review the [Perplexity AI docs](https://docs.perplexity.ai/)
- Open an issue on GitHub
