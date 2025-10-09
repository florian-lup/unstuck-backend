"""Voice Chat API routes using OpenAI Realtime API."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from clients.openai_client import OpenAIRealtimeClient
from core.auth import get_current_user
from core.config import settings
from core.rate_limit import RateLimited
from core.subscription import check_request_limits_only
from database.connection import get_db_session
from database.models import User
from schemas.auth import AuthenticatedUser
from schemas.voice_chat import VoiceChatSessionRequest, VoiceChatSessionResponse

router = APIRouter()


@router.post("/session", response_model=VoiceChatSessionResponse)
async def create_voice_session(
    request_data: VoiceChatSessionRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    internal_user: User = Depends(check_request_limits_only),  # noqa: B008
    db_session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: RateLimited = None,
) -> VoiceChatSessionResponse:
    """
    Create an ephemeral token for OpenAI Realtime API voice chat.

    This endpoint generates a short-lived token that your Electron client can use
    to establish a direct WebSocket connection to OpenAI's Realtime API.
    This architecture provides the lowest possible latency for voice interactions.

    **Security:** The ephemeral token expires in 60 seconds and is scoped to a
    single WebSocket session, ensuring your API key is never exposed to clients.

    **Request Limits:**
    - Free tier: 150 total requests (lifetime, never resets)
    - Community tier: 300 requests per month (resets every 30 days)

    **Client Implementation:**
    1. Detect the currently running game (Electron client handles this)
    2. Call this endpoint with the detected game name
    3. Connect to WebSocket URL using the returned ephemeral token
    4. Implement WebRTC or WebSocket audio streaming
    5. Handle real-time bidirectional audio communication
    
    **Note:** The Electron client automatically detects what game is running
    and sends it in the `game` parameter. Instructions are generated server-side
    based on the detected game.

    **Returns:**
    - `client_secret`: Use this as Bearer token for WebSocket auth
    - `websocket_url`: Connect to this URL
    - `expires_at`: Token expiration timestamp
    - `connection_instructions`: Step-by-step connection guide
    """
    try:
        # User limits already checked by check_request_limits_only
        # Store user ID in request state for rate limiting
        request.state.user_id = internal_user.auth0_user_id

        # Create OpenAI client
        openai_client = OpenAIRealtimeClient()

        # Generate ephemeral token with game-aware instructions
        # Voice is configured server-side in settings
        token_data = await openai_client.create_ephemeral_token(
            voice=settings.openai_realtime_voice,
            instructions=request_data.get_instructions(),
        )

        # Build response with connection instructions
        # Note: Browsers cannot set custom WebSocket headers, so we provide both methods:
        # 1. Query parameter with client_secret (for browsers/Electron renderer) - RECOMMENDED
        # 2. Header instructions (for Node.js clients)
        client_secret_value = token_data["client_secret"]["value"]
        browser_url = f"wss://api.openai.com/v1/realtime?model={token_data['model']}&client_secret={client_secret_value}"
        
        return VoiceChatSessionResponse(
            client_secret=client_secret_value,
            ephemeral_key_id=token_data["id"],
            model=token_data["model"],
            expires_at=token_data["client_secret"]["expires_at"],
            websocket_url=browser_url,  # Browser-friendly URL with client_secret as query param
            connection_instructions={
                "url_browser": browser_url,
                "url_nodejs": f"wss://api.openai.com/v1/realtime?model={token_data['model']}",
                "auth_method_browser": "client_secret included in URL as query parameter",
                "auth_method_nodejs": f"Set header: Authorization: Bearer {client_secret_value}",
                "protocol": "WebSocket",
                "expires_in_seconds": str(
                    token_data["client_secret"]["expires_at"] - int(request.state.request_id) // 1000000
                ),
                "note": "Connect immediately - token is valid for 60 seconds only. For browsers/Electron renderer, use websocket_url field (includes client_secret). For Node.js, use url_nodejs and set Authorization header.",
                "example_browser": (
                    f"const ws = new WebSocket('{browser_url}');"
                ),
                "example_nodejs": (
                    "const ws = new WebSocket('wss://api.openai.com/v1/realtime?model="
                    f"{token_data['model']}', [], {{ "
                    f"headers: {{ 'Authorization': 'Bearer {client_secret_value}' }} }})"
                ),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "session_creation_failed",
                "message": f"Failed to create voice chat session: {str(e)}",
                "request_id": getattr(request.state, "request_id", None),
            },
        ) from e


@router.get("/info")
async def get_voice_chat_info(
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> dict[str, Any]:
    """
    Get information about the voice chat feature and available options.

    Returns:
        - Available voice options
        - Model information
        - Connection requirements
        - Best practices for implementation
    """
    return {
        "feature": "OpenAI Realtime API Voice Chat",
        "model": "gpt-realtime-mini-2025-10-06",
        "voices": [
            {"name": "marin", "description": "Default voice - warm and friendly", "default": True},
            {"name": "cedar", "description": "Alternative voice - clear and professional", "default": False},
        ],
        "latency": "Optimized for real-time voice with <500ms response time",
        "connection_type": "WebSocket with ephemeral authentication",
        "token_lifetime": "60 seconds",
        "implementation_guide": {
            "step_1": "Call POST /api/v1/voice/session to get ephemeral token",
            "step_2": "Immediately connect WebSocket to the provided URL",
            "step_3": "Send audio frames via WebSocket",
            "step_4": "Receive real-time audio responses",
            "step_5": "Handle session expiration (60 seconds) and reconnect if needed",
            "browser_note": "For browsers/Electron renderer: Use the websocket_url field directly (client_secret included as query parameter). Example: new WebSocket(response.websocket_url)",
            "nodejs_note": "For Node.js: Use url_nodejs from connection_instructions and set Authorization header. Example: new WebSocket(url, [], { headers: { 'Authorization': 'Bearer TOKEN' } })",
        },
        "recommended_for": [
            "Real-time gaming voice assistance",
            "Live gameplay commentary",
            "Interactive voice-based game guides",
            "Voice-controlled game queries",
        ],
        "documentation": "https://platform.openai.com/docs/guides/realtime",
    }

