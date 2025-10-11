"""Voice Chat API routes using OpenAI Realtime API."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from clients.openai_client import OpenAIRealtimeClient
from core.auth import get_current_user
from core.config import settings
from core.rate_limit import RateLimited
from core.subscription import check_voice_request_limits_only
from database.connection import get_db_session
from database.models import User
from schemas.auth import AuthenticatedUser
from schemas.gaming_search import SearchRequest
from schemas.voice_chat import (
    ToolCallRequest,
    ToolCallResponse,
    VoiceChatSessionRequest,
    VoiceChatSessionResponse,
)
from services.gaming_search_service import search_service

router = APIRouter()
logger = logging.getLogger(__name__)


# Tool definitions for OpenAI Realtime API function calling
VOICE_CHAT_TOOLS = [
    {
        "type": "function",
        "name": "gaming_search",
        "description": (
            "Web search for current gaming information and any game-related content. "
            "Tool for retrieving fresh, up-to-date information that may have changed recently "
            "Supports multi-query search: you can provide multiple related queries (up to 5) "
            "in a single request for comprehensive research covering different aspects of a topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 5,
                        },
                    ],
                    "description": (
                        "Single search query string, OR an array of up to 5 related queries "
                        "for comprehensive multi-query search. "
                        "Example single: 'best League of Legends builds season 14'. "
                        "Example multi: ['League of Legends meta champions 2024', "
                        "'best ADC builds patch 14.1', 'jungle tier list current patch']"
                    ),
                },
            },
            "required": ["query"],
        },
    }
]


@router.post("/session", response_model=VoiceChatSessionResponse)
async def create_voice_session(
    request_data: VoiceChatSessionRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    internal_user: User = Depends(check_voice_request_limits_only),  # noqa: B008
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
    - Free tier: 60 total voice chat requests (lifetime, never resets)
    - Community tier: 150 voice chat requests per month (resets every 30 days)

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

        # Generate ephemeral token with game-aware instructions and tools
        # Voice is configured server-side in settings
        token_data = await openai_client.create_ephemeral_token(
            voice=settings.openai_realtime_voice,
            instructions=request_data.get_instructions(),
            tools=VOICE_CHAT_TOOLS,
        )

        # Build response with connection instructions
        # Note: Browsers cannot set custom WebSocket headers, so we provide both methods:
        # 1. Query parameter with client_secret (for browsers/Electron renderer) - RECOMMENDED
        # 2. Header instructions (for Node.js clients)
        
        # GA API response format: top-level 'value' and 'expires_at', session details nested
        client_secret_value = token_data["value"]
        session_data = token_data["session"]
        browser_url = f"wss://api.openai.com/v1/realtime?model={session_data['model']}&client_secret={client_secret_value}"
        
        return VoiceChatSessionResponse(
            client_secret=client_secret_value,
            ephemeral_key_id=session_data["id"],
            model=session_data["model"],
            expires_at=token_data["expires_at"],
            websocket_url=browser_url,  # Browser-friendly URL with client_secret as query param
            connection_instructions={
                "url_browser": browser_url,
                "url_nodejs": f"wss://api.openai.com/v1/realtime?model={session_data['model']}",
                "auth_method_browser": "client_secret included in URL as query parameter",
                "auth_method_nodejs": f"Set header: Authorization: Bearer {client_secret_value}",
                "protocol": "WebSocket",
                "expires_in_seconds": str(
                    token_data["expires_at"] - int(request.state.request_id) // 1000000
                ),
                "note": "Connect immediately - token is valid for 60 seconds only. For browsers/Electron renderer, use websocket_url field (includes client_secret). For Node.js, use url_nodejs and set Authorization header.",
                "example_browser": (
                    f"const ws = new WebSocket('{browser_url}');"
                ),
                "example_nodejs": (
                    "const ws = new WebSocket('wss://api.openai.com/v1/realtime?model="
                    f"{session_data['model']}', [], {{ "
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


@router.post("/tool-call", response_model=ToolCallResponse)
async def execute_tool_call(
    request_data: ToolCallRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    _: RateLimited = None,
) -> ToolCallResponse:
    """
    Execute a tool call from the OpenAI Realtime API.
    
    When the voice chat model decides to call a function (e.g., gaming_search),
    your client receives a function_call event from OpenAI. The client should:
    1. Extract the function name and arguments
    2. Call this endpoint with the function details
    3. Send the result back to OpenAI via the WebSocket
    
    **Supported Tools:**
    - gaming_search: Search for current gaming information
    
    **Returns:**
    - result: The function execution result
    - call_id: For tracking (if provided)
    - error: Error message if execution failed
    """
    try:
        logger.info(f"Tool call requested: {request_data.tool_name}")
        
        if request_data.tool_name == "gaming_search":
            # Extract arguments
            query = request_data.arguments.get("query")
            
            if not query:
                return ToolCallResponse(
                    call_id=request_data.call_id,
                    result={},
                    error="Missing required parameter: query",
                )
            
            # Execute the search
            try:
                search_request = SearchRequest(
                    query=query,
                )
                search_response = await search_service.search(search_request)
                
                # Format results for the model
                formatted_results = {
                    "query_type": "multi-query" if search_response.is_multi_query else "single-query",
                    "query": search_response.query,
                    "total_results": search_response.total_results,
                    "results": [
                        {
                            "title": result.title,
                            "url": result.url,
                            "snippet": result.snippet,
                        }
                        for result in search_response.results
                    ],
                }
                
                logger.info(
                    f"Gaming search completed: "
                    f"{'multi' if search_response.is_multi_query else 'single'}-query, "
                    f"{search_response.total_results} results"
                )
                
                return ToolCallResponse(
                    call_id=request_data.call_id,
                    result=formatted_results,
                    error=None,
                )
                
            except Exception as e:
                logger.error(f"Gaming search failed: {str(e)}")
                return ToolCallResponse(
                    call_id=request_data.call_id,
                    result={},
                    error=f"Search failed: {str(e)}",
                )
        
        else:
            # Unknown tool
            logger.warning(f"Unknown tool requested: {request_data.tool_name}")
            return ToolCallResponse(
                call_id=request_data.call_id,
                result={},
                error=f"Unknown tool: {request_data.tool_name}",
            )
            
    except Exception as e:
        logger.error(f"Tool call execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "tool_execution_failed",
                "message": f"Failed to execute tool: {str(e)}",
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
        "function_calling": {
            "enabled": True,
            "available_tools": [
                {
                    "name": "gaming_search",
                    "description": "Search for current gaming information with single or multi-query support",
                    "when_to_use": "Patch notes, current meta, recent updates, tier lists, builds",
                    "supports_multi_query": True,
                    "multi_query_info": {
                        "max_queries": 5,
                        "description": "Can accept up to 5 related queries in a single request for comprehensive research",
                        "example_single": "best League of Legends builds season 14",
                        "example_multi": [
                            "League of Legends meta champions 2024",
                            "best ADC builds patch 14.1",
                            "jungle tier list current patch"
                        ],
                    },
                }
            ],
            "workflow": [
                "1. Client connects to OpenAI WebSocket with ephemeral token",
                "2. Model decides to call a function and sends function_call event",
                "3. Client extracts function name and arguments from the event",
                "4. Client calls POST /api/v1/voice/tool-call with the function details",
                "5. Client sends the result back to OpenAI via WebSocket",
                "6. Model uses the result to provide an informed response",
            ],
        },
        "implementation_guide": {
            "step_1": "Call POST /api/v1/voice/session to get ephemeral token",
            "step_2": "Immediately connect WebSocket to the provided URL",
            "step_3": "Send audio frames via WebSocket",
            "step_4": "Receive real-time audio responses",
            "step_5": "Handle function_call events by calling POST /api/v1/voice/tool-call",
            "step_6": "Send function results back to OpenAI WebSocket",
            "step_7": "Handle session expiration (60 seconds) and reconnect if needed",
            "browser_note": "For browsers/Electron renderer: Use the websocket_url field directly (client_secret included as query parameter). Example: new WebSocket(response.websocket_url)",
            "nodejs_note": "For Node.js: Use url_nodejs from connection_instructions and set Authorization header. Example: new WebSocket(url, [], { headers: { 'Authorization': 'Bearer TOKEN' } })",
        },
        "recommended_for": [
            "Real-time gaming voice assistance",
            "Live gameplay commentary",
            "Interactive voice-based game guides",
            "Voice-controlled game queries",
            "Up-to-date gaming information retrieval",
        ],
        "documentation": "https://platform.openai.com/docs/guides/realtime",
    }

