"""Authentication and authorization schemas."""

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model from Auth0 JWT token."""

    sub: str = Field(..., description="Auth0 user ID (subject)")
    email: str | None = Field(default=None, description="User email address")
    email_verified: bool = Field(default=False, description="Email verification status")
    name: str | None = Field(default=None, description="User full name")
    nickname: str | None = Field(default=None, description="User nickname")
    picture: str | None = Field(default=None, description="User profile picture URL")
    updated_at: str | None = Field(default=None, description="Last updated timestamp")
    iss: str | None = Field(default=None, description="JWT issuer")
    aud: list[str] | str | None = Field(default=None, description="JWT audience")
    iat: int | None = Field(default=None, description="JWT issued at")
    exp: int | None = Field(default=None, description="JWT expiration time")
    scope: str | None = Field(default=None, description="JWT scopes")
    permissions: list[str] = Field(default_factory=list, description="User permissions")

    class Config:
        """Pydantic config."""

        extra = "allow"  # Allow additional fields from Auth0


class AuthenticatedUser(BaseModel):
    """Simplified authenticated user for internal use."""

    user_id: str = Field(..., description="Auth0 user ID")
    email: str | None = Field(default=None, description="User email")
    name: str | None = Field(default=None, description="User name")
    permissions: list[str] = Field(default_factory=list, description="User permissions")


class TokenData(BaseModel):
    """Token data for JWT processing."""

    sub: str | None = Field(default=None, description="Subject (user ID)")
    scopes: list[str] = Field(default_factory=list, description="Token scopes")
    permissions: list[str] = Field(default_factory=list, description="User permissions")


class AuthError(Exception):
    """Authentication error exception."""

    def __init__(self, error: str, description: str, status_code: int = 401) -> None:
        """Initialize authentication error."""
        self.error = error
        self.description = description
        self.status_code = status_code
        super().__init__(f"{error}: {description}")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: int = Field(..., description="Current timestamp")


class UserInfoResponse(BaseModel):
    """User information response."""

    user: AuthenticatedUser = Field(..., description="User information")
    conversation_count: int = Field(
        default=0, description="Number of active conversations"
    )
    last_activity: int | None = Field(
        default=None, description="Last activity timestamp"
    )
