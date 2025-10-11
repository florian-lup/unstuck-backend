"""Application configuration management."""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = Field(default="Gaming Chat Engine", description="Unstuck")
    debug: bool = Field(default=False, description="Debug mode")
    version: str = Field(default="0.1.0", description="Application version")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port", alias="PORT")

    # Security
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        description="Secret key for JWT encoding",
        alias="SECRET_KEY",
    )
    algorithm: str = Field(default="HS256", description="JWT encoding algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="JWT access token expiration time in minutes"
    )

    # Auth0
    auth0_domain: str = Field(..., description="Auth0 domain", alias="AUTH0_DOMAIN")
    auth0_api_audience: str = Field(
        ..., description="Auth0 API audience", alias="AUTH0_API_AUDIENCE"
    )
    auth0_issuer: str = Field(
        default="", description="Auth0 issuer URL (auto-generated from domain)"
    )
    auth0_jwks_url: str = Field(
        default="", description="Auth0 JWKS URL (auto-generated from domain)"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100, description="Rate limit: requests per minute"
    )
    rate_limit_window: int = Field(
        default=60, description="Rate limit: time window in seconds"
    )

    # Rate limiting is now handled in-memory (no Redis required)

    # Perplexity AI (Required)
    perplexity_api_key: str = Field(
        ..., description="Perplexity AI API key", alias="PERPLEXITY_API_KEY"
    )

    # OpenAI API (Required for voice chat)
    openai_api_key: str = Field(
        ..., description="OpenAI API key", alias="OPENAI_API_KEY"
    )

    # Stripe Configuration
    stripe_api_key: str = Field(
        ..., description="Stripe secret API key", alias="STRIPE_API_KEY"
    )
    stripe_webhook_secret: str = Field(
        ..., description="Stripe webhook signing secret", alias="STRIPE_WEBHOOK_SECRET"
    )
    stripe_price_id_community: str = Field(
        ...,
        description="Stripe price ID for Community tier",
        alias="STRIPE_PRICE_ID_COMMUNITY",
    )
    stripe_success_url: str = Field(
        default="http://localhost:3000/subscription/success",
        description="Checkout success redirect URL",
        alias="STRIPE_SUCCESS_URL",
    )
    stripe_cancel_url: str = Field(
        default="http://localhost:3000/subscription/cancel",
        description="Checkout cancel redirect URL",
        alias="STRIPE_CANCEL_URL",
    )

    # Database Configuration (Neon PostgreSQL)
    database_url: str = Field(
        ...,
        description="Database connection URL for Neon PostgreSQL",
        alias="DATABASE_URL",
    )
    database_pool_size: int = Field(
        default=20, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=30, description="Database connection pool max overflow"
    )
    use_null_pool: bool = Field(
        default=True, description="Use NullPool for serverless environments like Neon"
    )

    # CORS - Updated for Electron app and Railway deployment
    allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "capacitor://localhost",
            "ionic://localhost",
            "http://localhost",
            "http://127.0.0.1",
            "https://*.railway.app",
            "https://*.up.railway.app",
        ],
        description="CORS allowed origins - includes Electron app origins and Railway domains",
    )
    allowed_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="CORS allowed methods",
    )
    allowed_headers: list[str] = Field(
        default=["*"], description="CORS allowed headers"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings and auto-generate Auth0 URLs."""
        super().__init__(**kwargs)

        # Auto-generate Auth0 URLs if not provided
        if not self.auth0_issuer and self.auth0_domain:
            self.auth0_issuer = f"https://{self.auth0_domain}/"

        if not self.auth0_jwks_url and self.auth0_domain:
            self.auth0_jwks_url = f"https://{self.auth0_domain}/.well-known/jwks.json"


# Global settings instance
settings = Settings()
