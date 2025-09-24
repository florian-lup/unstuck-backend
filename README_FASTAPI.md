# Gaming Search Engine - FastAPI Backend

A secure, production-ready FastAPI backend for the Gaming Search Engine with Auth0 JWT authentication.

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Poetry (dependency management)
- Auth0 account and application
- Perplexity AI API key

### Installation

1. **Install dependencies**:

   ```bash
   poetry install
   ```

2. **Set up environment variables**:
   Create a `.env` file in the project root:

   ```bash
   # Application Settings
   DEBUG=true  # Set to false in production
   HOST=0.0.0.0
   PORT=8000

   # Auth0 Configuration (Required)
   AUTH0_DOMAIN=your-domain.auth0.com
   AUTH0_API_AUDIENCE=https://your-gaming-search-api/

   # Perplexity AI API (Required)
   PERPLEXITY_API_KEY=your-perplexity-api-key

   # Security
   SECRET_KEY=your-super-secret-key-change-in-production

   # Rate Limiting
   RATE_LIMIT_REQUESTS=100
   RATE_LIMIT_WINDOW=60
   ```

3. **Run the server**:

   ```bash
   # Development mode
   poetry run python main.py

   # Or using uvicorn directly
   poetry run uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🔧 Configuration

### Auth0 Setup

1. Create an Auth0 application (Single Page Application)
2. Configure the following settings:

   - **Allowed Callback URLs**: `http://localhost:3000/callback` (adjust for your Electron app)
   - **Allowed Web Origins**: `http://localhost:3000`
   - **Allowed Logout URLs**: `http://localhost:3000`

3. Create an Auth0 API:
   - **Identifier**: `https://your-gaming-search-api/` (must match `AUTH0_API_AUDIENCE`)
   - **Signing Algorithm**: RS256

### Environment Variables

| Variable              | Required | Description                 | Default        |
| --------------------- | -------- | --------------------------- | -------------- |
| `AUTH0_DOMAIN`        | Yes      | Your Auth0 domain           | -              |
| `AUTH0_API_AUDIENCE`  | Yes      | Auth0 API identifier        | -              |
| `PERPLEXITY_API_KEY`  | Yes      | Perplexity AI API key       | -              |
| `DEBUG`               | No       | Enable debug mode           | `false`        |
| `HOST`                | No       | Server host                 | `0.0.0.0`      |
| `PORT`                | No       | Server port                 | `8000`         |
| `SECRET_KEY`          | No       | JWT secret key              | Auto-generated |
| `RATE_LIMIT_REQUESTS` | No       | Requests per minute         | `100`          |
| `RATE_LIMIT_WINDOW`   | No       | Rate limit window (seconds) | `60`           |

## 📚 API Documentation

### Authentication

All endpoints (except health checks and public search) require a valid Auth0 JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Endpoints

#### Health & Status

- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

#### Authentication

- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/verify` - Verify JWT token
- `GET /api/v1/auth/permissions` - Get user permissions

#### Gaming Search

- `POST /api/v1/gaming/search` - Authenticated search
- `POST /api/v1/gaming/search/public` - Public search (optional auth)
- `GET /api/v1/gaming/conversations` - List user conversations
- `GET /api/v1/gaming/conversations/{id}/history` - Get conversation history
- `DELETE /api/v1/gaming/conversations/{id}` - Clear conversation

### Interactive API Documentation

When running in debug mode, access the interactive API documentation at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔒 Security Features

### Authentication & Authorization

- Auth0 JWT token validation
- RS256 signature verification
- Automatic token refresh handling
- Permission-based access control

### Security Headers

- Content Security Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
- Referrer-Policy

### Rate Limiting

- In-memory sliding window rate limiting
- Per-user and per-IP limits
- Rate limit headers in responses
- No external dependencies required

### Input Validation

- Pydantic model validation
- SQL injection prevention
- XSS protection
- Request size limiting

### CORS Configuration

- Electron app-friendly CORS settings
- Configurable allowed origins
- Credential support for authenticated requests

## 🏗️ Architecture

### Project Structure

```
├── api/                    # API layer
│   ├── app.py             # FastAPI application
│   └── routes/            # API route handlers
│       ├── auth.py        # Authentication routes
│       ├── gaming_search.py # Gaming search routes
│       └── health.py      # Health check routes
├── core/                  # Core functionality
│   ├── auth.py           # Auth0 JWT authentication
│   ├── config.py         # Application configuration
│   └── rate_limit.py     # Rate limiting middleware
├── schemas/              # Pydantic schemas
│   ├── auth.py          # Authentication schemas
│   └── gaming_search.py # Gaming search schemas
├── services/            # Business logic
│   └── gaming_search_service.py # Search service
└── clients/            # External API clients
    └── perplexity_client.py # Perplexity AI client
```

### Key Components

1. **Authentication**: Auth0 JWT verification with automatic key rotation
2. **Rate Limiting**: Redis-based sliding window rate limiting
3. **Error Handling**: Comprehensive error handling with user-friendly messages
4. **Middleware**: Security headers, CORS, request timing, and logging
5. **Validation**: Input validation using Pydantic models

## 🚀 Production Deployment

### Using Gunicorn

```bash
poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.app:app --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
COPY . .

EXPOSE 8000
CMD ["poetry", "run", "gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "api.app:app", "--bind", "0.0.0.0:8000"]
```

### Environment Checklist for Production

- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure Redis for rate limiting
- [ ] Set up HTTPS/TLS
- [ ] Configure proper CORS origins
- [ ] Set up monitoring and logging
- [ ] Configure rate limits appropriately
- [ ] Set up health check endpoints for load balancer

## 🔍 Monitoring

### Health Checks

The API provides multiple health check endpoints for monitoring:

- `/api/v1/health` - Basic health status
- `/api/v1/health/ready` - Kubernetes readiness probe
- `/api/v1/health/live` - Kubernetes liveness probe

### Request Tracing

Every request includes:

- `X-Request-ID` - Unique request identifier
- `X-Process-Time` - Request processing time
- Rate limit headers when applicable

### Logging

The application logs:

- Request/response information
- Authentication events
- Rate limiting events
- Errors and exceptions

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=.
```

### Testing Authentication

```bash
# Get a test token from Auth0
curl -X POST "https://your-domain.auth0.com/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "audience": "https://your-gaming-search-api/",
    "grant_type": "client_credentials"
  }'

# Test authenticated endpoint
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer your-jwt-token"
```

## 🤝 Integration with Electron Client

See [CLIENT_IMPLEMENTATION.md](CLIENT_IMPLEMENTATION.md) for detailed integration guide including:

- Auth0 setup in Electron
- API client implementation
- Error handling strategies
- Security best practices
- Complete code examples

## 🐛 Troubleshooting

### Common Issues

1. **Auth0 Token Verification Fails**

   - Check `AUTH0_DOMAIN` and `AUTH0_API_AUDIENCE` values
   - Ensure JWT token is valid and not expired
   - Verify Auth0 API settings (RS256 algorithm)

2. **Rate Limiting Not Working**

   - Check Redis connection (`REDIS_URL`)
   - Falls back to memory-based limiting if Redis unavailable

3. **CORS Issues**

   - Add your Electron app origin to `ALLOWED_ORIGINS`
   - Include protocol (http/https) in origins

4. **High Memory Usage**
   - Conversation history is stored in memory
   - Consider implementing database storage for production

### Debug Mode

Enable debug mode by setting `DEBUG=true` in your `.env` file to get:

- Detailed error messages
- API documentation endpoints
- Request/response logging
- Additional health check information

## 📝 License

This project is part of the Gaming Search Engine and follows the same licensing terms.
