"""Voice chat WebSocket endpoints."""

import base64
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from schemas.voice_chat import (
    AudioChunkMessage,
    AudioEndMessage,
    AudioStreamChunkMessage,
    AudioStreamEndMessage,
    AudioStreamStartMessage,
    EndSessionMessage,
    ErrorMessage,
    MessageType,
    SessionEndedMessage,
    SessionStartedMessage,
    StartSessionMessage,
)
from services.voice_chat_service import voice_chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """
        Connect a WebSocket.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str) -> None:
        """
        Disconnect a WebSocket.

        Args:
            session_id: Session identifier
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")

    async def send_json(self, session_id: str, message: dict[str, Any]) -> None:
        """
        Send JSON message to a WebSocket.

        Args:
            session_id: Session identifier
            message: Message to send
        """
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def send_bytes(self, session_id: str, data: bytes) -> None:
        """
        Send bytes to a WebSocket.

        Args:
            session_id: Session identifier
            data: Bytes to send
        """
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_bytes(data)


manager = WebSocketConnectionManager()


async def handle_start_session(data: dict[str, Any], websocket: WebSocket, already_accepted: bool = False) -> None:
    """
    Handle start session message.

    Args:
        data: Message data
        websocket: WebSocket connection
        already_accepted: Whether the websocket has already been accepted
    """
    try:
        message = StartSessionMessage(**data)
        session_id = message.session_id

        # Create session in service (uses backend-configured system prompt and voice)
        voice_chat_service.create_session(session_id)

        # Store WebSocket connection
        if already_accepted:
            # WebSocket already accepted, just register it
            manager.active_connections[session_id] = websocket
            logger.info(f"WebSocket registered for session: {session_id}")
        else:
            # Accept and register the connection
            await manager.connect(session_id, websocket)

        # Send confirmation
        response = SessionStartedMessage(session_id=session_id)
        await manager.send_json(session_id, response.model_dump())

    except Exception as e:
        logger.error(f"Error starting session: {e}")
        error_response = ErrorMessage(
            session_id=data.get("session_id"),
            error=str(e),
            code="session_start_error"
        )
        await websocket.send_json(error_response.model_dump())


async def handle_audio_chunk(data: dict[str, Any]) -> None:
    """
    Handle audio chunk message.

    Args:
        data: Message data
    """
    try:
        message = AudioChunkMessage(**data)
        session_id = message.session_id

        # Store audio chunk for later processing
        # For now, we'll accumulate chunks until we get an AUDIO_END message
        # In a production system, you might want to use a buffer or queue
        if not hasattr(voice_chat_service, '_audio_buffers'):
            voice_chat_service._audio_buffers = {}  # type: ignore

        if session_id not in voice_chat_service._audio_buffers:  # type: ignore
            voice_chat_service._audio_buffers[session_id] = {  # type: ignore
                'chunks': [],
                'format': message.format
            }

        # Decode base64 audio data
        audio_bytes = base64.b64decode(message.audio_data)
        voice_chat_service._audio_buffers[session_id]['chunks'].append(audio_bytes)  # type: ignore

    except Exception as e:
        logger.error(f"Error handling audio chunk: {e}")
        error_response = ErrorMessage(
            session_id=data.get("session_id"),
            error=str(e),
            code="audio_chunk_error"
        )
        await manager.send_json(data.get("session_id", ""), error_response.model_dump())


async def handle_audio_end(data: dict[str, Any]) -> None:
    """
    Handle audio end message - process complete audio.

    Args:
        data: Message data
    """
    try:
        message = AudioEndMessage(**data)
        session_id = message.session_id

        # Get accumulated audio chunks
        if not hasattr(voice_chat_service, '_audio_buffers'):
            raise ValueError("No audio data received")

        buffer_data = voice_chat_service._audio_buffers.get(session_id)
        if not buffer_data:
            raise ValueError("No audio data for session")

        # Combine all chunks
        audio_data = b''.join(buffer_data['chunks'])
        audio_format = buffer_data['format']

        # Clear buffer
        del voice_chat_service._audio_buffers[session_id]

        logger.info(f"Processing audio end for session {session_id}, {len(audio_data)} bytes")

        # Process audio through the pipeline
        # Step 1: Transcribe
        transcribed_text = await voice_chat_service.process_audio_to_text(
            audio_data,
            audio_format
        )

        # Step 2: Generate response
        response_text = await voice_chat_service.generate_text_response(
            session_id,
            transcribed_text
        )

        # Step 3: Convert to speech and stream (uses backend-configured voice)
        # Send stream start
        stream_start = AudioStreamStartMessage(session_id=session_id)
        await manager.send_json(session_id, stream_start.model_dump())

        # Stream audio chunks using session's voice
        async for audio_chunk in voice_chat_service.text_to_audio_stream(session_id, response_text):
            chunk_message = AudioStreamChunkMessage(
                session_id=session_id,
                audio_data=base64.b64encode(audio_chunk).decode('utf-8')
            )
            await manager.send_json(session_id, chunk_message.model_dump())

        # Send stream end
        stream_end = AudioStreamEndMessage(session_id=session_id)
        await manager.send_json(session_id, stream_end.model_dump())

    except Exception as e:
        logger.error(f"Error processing audio end: {e}")
        error_response = ErrorMessage(
            session_id=data.get("session_id"),
            error=str(e),
            code="audio_processing_error"
        )
        await manager.send_json(data.get("session_id", ""), error_response.model_dump())


async def handle_end_session(data: dict[str, Any]) -> None:
    """
    Handle end session message.

    Args:
        data: Message data
    """
    try:
        message = EndSessionMessage(**data)
        session_id = message.session_id

        # Clear session
        voice_chat_service.clear_session(session_id)

        # Clean up any remaining audio buffers
        if hasattr(voice_chat_service, '_audio_buffers') and session_id in voice_chat_service._audio_buffers:
            del voice_chat_service._audio_buffers[session_id]

        # Send confirmation
        response = SessionEndedMessage(session_id=session_id)
        await manager.send_json(session_id, response.model_dump())

        # Disconnect WebSocket
        manager.disconnect(session_id)

    except Exception as e:
        logger.error(f"Error ending session: {e}")
        error_response = ErrorMessage(
            session_id=data.get("session_id"),
            error=str(e),
            code="session_end_error"
        )
        await manager.send_json(data.get("session_id", ""), error_response.model_dump())


@router.websocket("/ws")
async def voice_chat_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for voice chat.

    This endpoint handles bidirectional communication for voice chat:
    - Receives audio chunks from client
    - Sends transcription, response text, and audio response back to client
    """
    # Accept WebSocket connection first (required before any send/receive)
    await websocket.accept()
    
    session_id = None

    try:
        # Wait for start session message first
        data = await websocket.receive_json()
        message_type = data.get("type")

        if message_type != MessageType.START_SESSION.value:
            error_response = ErrorMessage(
                session_id=None,
                error="First message must be START_SESSION",
                code="invalid_first_message"
            )
            await websocket.send_json(error_response.model_dump())
            await websocket.close()
            return

        # Handle start session (websocket already accepted above)
        await handle_start_session(data, websocket, already_accepted=True)
        session_id = data.get("session_id")

        # Process messages
        while True:
            # Receive message
            message = await websocket.receive_json()
            message_type = message.get("type")

            logger.info(f"Received message type: {message_type} for session {session_id}")

            # Route message to appropriate handler
            if message_type == MessageType.AUDIO_CHUNK.value:
                await handle_audio_chunk(message)

            elif message_type == MessageType.AUDIO_END.value:
                await handle_audio_end(message)

            elif message_type == MessageType.END_SESSION.value:
                await handle_end_session(message)
                break

            else:
                logger.warning(f"Unknown message type: {message_type}")
                error_response = ErrorMessage(
                    session_id=session_id,
                    error=f"Unknown message type: {message_type}",
                    code="unknown_message_type"
                )
                await manager.send_json(session_id or "", error_response.model_dump())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
        if session_id:
            voice_chat_service.clear_session(session_id)
            manager.disconnect(session_id)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if session_id:
            error_response = ErrorMessage(
                session_id=session_id,
                error=str(e),
                code="websocket_error"
            )
            await manager.send_json(session_id, error_response.model_dump())
            voice_chat_service.clear_session(session_id)
            manager.disconnect(session_id)

