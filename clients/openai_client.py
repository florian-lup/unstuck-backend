"""OpenAI client for Realtime API ephemeral tokens."""

from typing import Any

import httpx

from core.config import settings


class OpenAIRealtimeClient:
    """Client for OpenAI Realtime API with ephemeral token generation."""

    def __init__(self) -> None:
        """Initialize OpenAI Realtime client."""
        self.api_key = settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"
        self.model = settings.openai_realtime_model

    async def create_ephemeral_token(
        self,
        voice: str = "marin",
        instructions: str | None = None,
    ) -> dict[str, Any]:
        """
        Create an ephemeral token for client-side Realtime API access (GA version).

        This token is short-lived (typically 1 minute) and can be safely used
        in client applications without exposing your primary API key.

        Uses the GA (General Availability) endpoint: /v1/realtime/client_secrets

        Args:
            voice: Voice to use for audio responses.
                   Options: marin (default), cedar
            instructions: System instructions for the AI assistant

        Returns:
            dict containing (GA API format):
                - value: The ephemeral client secret token string
                - expires_at: Unix timestamp when token expires (typically 60 seconds)
                - session: Object containing session configuration
                  - id: Unique identifier for the session
                  - model: Model being used
                  - instructions: The instructions configured for the session
                  - audio: Audio configuration including voice, format, etc.

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/realtime/client_secrets"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build the session configuration according to GA API format
        session_config: dict[str, Any] = {
            "type": "realtime",  # Required for GA API
            "model": self.model,
            "audio": {
                "output": {
                    "voice": voice,
                }
            },
        }

        # Add optional parameters
        if instructions:
            session_config["instructions"] = instructions

        # Note: max_response_output_tokens is not supported in GA API
        # The parameter has been removed from the GA interface
        
        # Wrap in session object as required by GA API
        payload = {"session": session_config}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

