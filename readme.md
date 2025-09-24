# Gaming Search Engine

An AI-powered gaming search engine built with Perplexity AI. This tool allows users to search for gaming information using natural language queries with conversation context.

## Features

- 🎮 **Gaming-focused AI search** - Specialized prompts for gaming content
- 💬 **Multi-step conversations** - Maintains conversation context across requests
- 🔍 **Advanced search filters** - Time-based filtering and search customization
- 📊 **Usage analytics** - Token usage and performance metrics
- 🚀 **Modern Python** - Built with Python 3.13 and Poetry
- 🖥️ **Command line interface** - Easy-to-use testing tools

## Project Structure

```
unstuck-backend/
├── clients/
│   ├── perplexity_client.py     # Perplexity API client
│   └── __init__.py
├── core/
│   ├── config.py                # Application configuration
│   ├── constants.py             # Application constants
│   └── exceptions.py            # Core exceptions
├── schemas/
│   ├── gaming_search.py         # Request/response schemas
│   └── __init__.py
├── services/
│   ├── gaming_search_service.py # Business logic and conversation management
│   └── __init__.py
├── utils/
│   ├── exceptions.py            # Custom exceptions
│   └── __init__.py
├── main.py                      # Application entry point
├── test_gaming_search.py       # Gaming search testing interface
├── test_setup.py               # Setup validation script
├── pyproject.toml              # Poetry configuration
└── .env.example                # Environment variables template
```

## Quick Start

### Prerequisites

- Python 3.13+
- Poetry (for dependency management)
- Perplexity AI API key

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

4. **Get your Perplexity API key:**
   - Visit the [Perplexity API Portal](https://docs.perplexity.ai/getting-started/quickstart)
   - Navigate to the **API Keys** tab and generate a new key
   - Add it to your `.env` file:
     ```
     PERPLEXITY_API_KEY=your_api_key_here
     ```

### Running the Application

1. **Application entry point (status & info):**

   ```bash
   poetry run python main.py
   ```

2. **Gaming search testing:**

   ```bash
   # Single query test
   poetry run python test_gaming_search.py "What are the best RPG games of 2024?"

   # Interactive mode with conversation context
   poetry run python test_gaming_search.py --interactive

   # Test conversation context with predefined queries
   poetry run python test_gaming_search.py --conversation

   # Show help and options
   poetry run python test_gaming_search.py --help
   ```

3. **Validate setup:**
   ```bash
   poetry run python test_setup.py
   ```

## Usage Examples

### Single Query Testing

```bash
# Test specific gaming questions
poetry run python test_gaming_search.py "What are the best indie games of 2024?"
poetry run python test_gaming_search.py "Compare PS5 vs Xbox Series X performance"
poetry run python test_gaming_search.py "Tell me about Elden Ring gameplay mechanics"
```

### Interactive Testing Mode

```bash
poetry run python test_gaming_search.py --interactive

# Then ask questions interactively with conversation context:
🎮 Ask a gaming question (or 'quit'): Tell me about Elden Ring
🎮 Ask a gaming question (or 'quit'): What about its DLC content?
🎮 Ask a gaming question (or 'quit'): How does it compare to other FromSoftware games?
🎮 Ask a gaming question (or 'quit'): quit
```

### Conversation Context Testing

```bash
# Test predefined conversation flow to verify context works
poetry run python test_gaming_search.py --conversation
```

## Features

### 🎯 Gaming-Optimized Search

- Specialized AI prompts for gaming content
- Comprehensive game information including platforms, release dates, and features
- Gaming hardware comparisons and recommendations
- Industry news and trends

### 💬 Conversation Context

- Maintains conversation history across multiple queries
- Follow-up questions understand previous context
- Each conversation gets a unique ID for tracking

## Configuration

Key configuration options in your `.env` file:

```bash
# Required
PERPLEXITY_API_KEY=your_api_key_here

# Optional
DEBUG=false                  # Debug mode
SECRET_KEY=your-secret-key   # For future JWT tokens
```

## Search Parameters

The API supports various search parameters:

- **model**: `sonar` (default)
- **search_context_size**: `low` (default for efficiency)
- **temperature**: 0.2 (default for focused responses)

### 📦 Core Dependencies

```toml
"pydantic (>=2.11.9,<3.0.0)",       # Data validation and serialization
"pydantic-settings (>=2.10.1,<3.0.0)", # Configuration management
"perplexityai (>=0.10.0,<0.11.0)"   # Official Perplexity SDK
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
- **`test_gaming_search.py`** - Comprehensive testing interface with multiple modes
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

- Check the application help: `python test_gaming_search.py --help`
- Validate your setup: `python test_setup.py`
- Review the [Perplexity AI docs](https://docs.perplexity.ai/)
- Open an issue on GitHub
