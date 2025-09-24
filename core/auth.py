"""Auth0 JWT authentication and authorization."""

import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import settings
from schemas.auth import AuthenticatedUser, AuthError, User


class Auth0JWTBearer(HTTPBearer):
    """Auth0 JWT Bearer token authentication."""

    def __init__(self, auto_error: bool = True):
        """Initialize Auth0 JWT Bearer."""
        super().__init__(auto_error=auto_error)
        self._jwks_cache: dict[str, Any] = {}
        self._cache_expiry: int = 0

    async def get_jwks(self) -> dict[str, Any]:
        """Get JSON Web Key Set from Auth0."""
        # Check cache first
        current_time = int(time.time())
        if self._jwks_cache and current_time < self._cache_expiry:
            return self._jwks_cache

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.auth0_jwks_url)
                response.raise_for_status()
                jwks = response.json()

                # Cache for 1 hour
                self._jwks_cache = jwks
                self._cache_expiry = current_time + 3600

                return jwks  # type: ignore[no-any-return]

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to fetch JWKS: {e}",
            ) from e

    def get_rsa_key(
        self, token_header: dict[str, Any], jwks: dict[str, Any]
    ) -> dict[str, Any]:
        """Get RSA key for token verification."""
        rsa_key = {}

        if "kid" not in token_header:
            raise AuthError(
                error="invalid_header",
                description="Authorization malformed: missing kid",
                status_code=401,
            )

        for key in jwks.get("keys", []):
            if key["kid"] == token_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise AuthError(
                error="invalid_header",
                description="Unable to find appropriate key",
                status_code=401,
            )

        return rsa_key

    async def verify_token(self, token: str) -> User:
        """Verify and decode JWT token."""
        try:
            # Get token header
            try:
                token_header = jwt.get_unverified_header(token)
            except JWTError as e:
                raise AuthError(
                    error="invalid_header",
                    description="Invalid header: Use an RS256 signed JWT Access Token",
                    status_code=401,
                ) from e

            # Get JWKS
            jwks = await self.get_jwks()

            # Get RSA key
            rsa_key = self.get_rsa_key(token_header, jwks)

            # Verify and decode token
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=["RS256"],
                    audience=settings.auth0_api_audience,
                    issuer=settings.auth0_issuer,
                )
            except jwt.ExpiredSignatureError as e:
                raise AuthError(
                    error="token_expired",
                    description="Token has expired",
                    status_code=401,
                ) from e
            except jwt.InvalidAudienceError as e:
                raise AuthError(
                    error="invalid_audience",
                    description="Invalid audience",
                    status_code=401,
                ) from e
            except jwt.InvalidIssuerError as e:
                raise AuthError(
                    error="invalid_issuer",
                    description="Invalid issuer",
                    status_code=401,
                ) from e
            except jwt.InvalidSignatureError as e:
                raise AuthError(
                    error="invalid_signature",
                    description="Invalid signature",
                    status_code=401,
                ) from e
            except jwt.InvalidTokenError as e:
                raise AuthError(
                    error="invalid_token",
                    description="Invalid token",
                    status_code=401,
                ) from e

            # Create User object
            return User(**payload)

        except AuthError:
            raise
        except Exception as e:
            raise AuthError(
                error="invalid_token",
                description=f"Unable to parse authentication token: {e}",
                status_code=401,
            ) from e

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> User:  # noqa: B008
        """Validate JWT token and return user."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token missing",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            return await self.verify_token(credentials.credentials)
        except AuthError as e:
            raise HTTPException(
                status_code=e.status_code,
                detail={"error": e.error, "description": e.description},
                headers={"WWW-Authenticate": "Bearer"},
            ) from e


# Global instances
auth0_jwt_bearer = Auth0JWTBearer()


async def get_current_user(user: User = Depends(auth0_jwt_bearer)) -> AuthenticatedUser:  # noqa: B008
    """Get current authenticated user."""
    permissions = []

    # Extract permissions from scope or permissions claim
    if user.scope:
        permissions.extend(user.scope.split())

    if user.permissions:
        permissions.extend(user.permissions)

    # Remove duplicates while preserving order
    permissions = list(dict.fromkeys(permissions))

    return AuthenticatedUser(
        user_id=user.sub,
        email=user.email,
        name=user.name or user.nickname,
        permissions=permissions,
    )


def require_permission(permission: str) -> Any:
    """Dependency to require specific permission."""

    def permission_checker(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:  # noqa: B008
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        return user

    return permission_checker


def require_any_permission(*permissions: str) -> Any:
    """Dependency to require any of the specified permissions."""

    def permission_checker(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:  # noqa: B008
        if not any(perm in user.permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permissions)}",
            )
        return user

    return permission_checker


# Optional authentication - returns None if not authenticated
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),  # noqa: B008
) -> AuthenticatedUser | None:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        auth_bearer = Auth0JWTBearer(auto_error=False)
        user = await auth_bearer.verify_token(credentials.credentials)
        return await get_current_user(user)
    except (AuthError, HTTPException):
        return None
