"""Application configuration management."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Unstuck Backend"
    debug: bool = False
    version: str = "0.1.0"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Perplexity AI
    perplexity_api_key: str | None = None
    
    # Security
    secret_key: str | None = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
