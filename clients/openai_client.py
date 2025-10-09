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
        voice: str = "alloy",
        instructions: str | None = None,
        max_response_output_tokens: int | str = "inf",
    ) -> dict[str, Any]:
        """
        Create an ephemeral token for client-side Realtime API access (GA version).

        This token is short-lived (typically 1 minute) and can be safely used
        in client applications without exposing your primary API key.

        Uses the GA (General Availability) endpoint: /v1/realtime/client_secrets

        Args:
            voice: Voice to use for audio responses.
                   Options: alloy, echo, shimmer, ash, ballad, coral, sage, verse
            instructions: System instructions for the AI assistant
            max_response_output_tokens: Maximum tokens in response ("inf" for unlimited)

        Returns:
            dict containing:
                - client_secret: Ephemeral token for WebSocket connection
                - ephemeral_key_id: Unique identifier for the ephemeral key
                - model: Model being used
                - expires_at: Unix timestamp when token expires (typically 60 seconds)

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/realtime/client_secrets"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "voice": voice,
        }

        # Add optional parameters
        if instructions:
            payload["instructions"] = instructions

        if max_response_output_tokens:
            payload["max_response_output_tokens"] = max_response_output_tokens

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

