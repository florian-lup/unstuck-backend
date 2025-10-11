# Voice Chat Implementation

This document describes the voice chat implementation using WebSockets for real-time audio communication.

## Architecture

The voice chat system follows a client-server architecture with real-time bidirectional communication:

```
┌─────────────┐                          ┌─────────────┐
│   Electron  │                          │   Backend   │
│   (Client)  │◄────────WebSocket───────►│   (Python)  │
└─────────────┘                          └─────────────┘
       │                                        │
       │                                        │
   Microphone                              OpenAI APIs
       │                                        │
       ├─ Capture wav audio                    ├─ gpt-4o-transcribe
       ├─ Send chunks via WS                   │  (Transcription)
       │                                        │
       │                                        ├─ gpt-5-mini
       │                                        │  (Response Generation)
       │                                        │
       │◄───── Receive audio stream             ├─ gpt-4o-mini-tts
       │                                        │  (Text-to-Speech)
   Play Audio                                   │
```

## OpenAI Models Used

1. **Speech-to-Text**: `gpt-4o-transcribe` via `/v1/audio/transcriptions`
2. **Response Generation**: `gpt-5-mini` via `/v1/responses` (Chat Completions API)
3. **Text-to-Speech**: `gpt-4o-mini-tts` via `/v1/audio/speech`

## Backend Setup

### 1. Environment Variables

Add the following to your `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

**Voice and System Prompt Configuration**: These are defined as constants in `clients/openai_client.py`:

- `DEFAULT_TTS_VOICE = "alloy"`
- `DEFAULT_SYSTEM_PROMPT = "You are a helpful gaming assistant..."`

To change these, edit the constants directly in the file.

### 2. Install Dependencies

```bash
poetry install
```

This will install:

- `openai>=1.59.8` - OpenAI Python client
- `websockets>=13.1` - WebSocket support
- All other existing dependencies

### 3. Run the Server

```bash
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## WebSocket Endpoint

**Endpoint**: `ws://localhost:8000/api/v1/voice/ws`

## Message Protocol

All messages are JSON objects with a `type` field that determines the message structure.

### Client → Server Messages

#### 1. Start Session

```json
{
  "type": "start_session",
  "session_id": "unique_session_id"
}
```

**Note**: System prompt and TTS voice are configured on the backend as constants in `clients/openai_client.py`. This ensures consistent behavior and prevents clients from overriding system settings.

#### 2. Audio Chunk

```json
{
  "type": "audio_chunk",
  "session_id": "session_id",
  "audio_data": "base64_encoded_audio",
  "format": "wav"
}
```

Send multiple chunks as the user speaks.

#### 3. Audio End

```json
{
  "type": "audio_end",
  "session_id": "session_id"
}
```

Signal that the user has finished speaking. This triggers processing.

#### 4. End Session

```json
{
  "type": "end_session",
  "session_id": "session_id"
}
```

### Server → Client Messages

#### 1. Session Started

```json
{
  "type": "session_started",
  "session_id": "session_id"
}
```

#### 2. Transcription

```json
{
  "type": "transcription",
  "session_id": "session_id",
  "text": "transcribed text from user audio"
}
```

#### 3. Response Text

```json
{
  "type": "response_text",
  "session_id": "session_id",
  "text": "AI generated response text"
}
```

#### 4. Audio Stream Start

```json
{
  "type": "audio_stream_start",
  "session_id": "session_id"
}
```

#### 5. Audio Stream Chunk

```json
{
  "type": "audio_stream_chunk",
  "session_id": "session_id",
  "audio_data": "base64_encoded_pcm_audio"
}
```

Multiple chunks will be sent.

#### 6. Audio Stream End

```json
{
  "type": "audio_stream_end",
  "session_id": "session_id"
}
```

#### 7. Error

```json
{
  "type": "error",
  "session_id": "session_id",
  "error": "error message",
  "code": "error_code"
}
```

#### 8. Session Ended

```json
{
  "type": "session_ended",
  "session_id": "session_id"
}
```

## Flow

### Typical Voice Chat Flow

1. **Client connects** to WebSocket endpoint
2. **Client sends** `start_session` message
3. **Server responds** with `session_started`
4. **User speaks** → Client captures audio → Client sends multiple `audio_chunk` messages
5. **User stops speaking** → Client sends `audio_end` message
6. **Server processes**:
   - Transcribes audio (STT)
   - Sends `transcription` message to client
   - Generates response using LLM
   - Sends `response_text` message to client
   - Converts response to speech (TTS)
   - Sends `audio_stream_start` message
   - Streams audio chunks via `audio_stream_chunk` messages
   - Sends `audio_stream_end` message
7. **Client plays** audio response
8. Repeat steps 4-7 for continued conversation
9. **Client sends** `end_session` when done
10. **Server responds** with `session_ended` and closes connection

## Audio Format

### Input (Client → Server)

- **Format**: WAV
- **Sample Rate**: 16kHz recommended
- **Channels**: Mono (1 channel)
- **Encoding**: Base64 string in JSON

### Output (Server → Client)

- **Format**: PCM (raw audio)
- **Sample Rate**: Determined by TTS model
- **Channels**: Mono (1 channel)
- **Encoding**: Base64 string in JSON

## Electron Client Implementation

See `voice_chat_client_example.js` for a complete example implementation.

### Key Features

1. **WebSocket Management**: Connect, send, receive, disconnect
2. **Audio Capture**: Use Web Audio API to capture microphone input
3. **Audio Streaming**: Send audio chunks in real-time
4. **Audio Playback**: Play received audio chunks for low latency
5. **Event Handlers**: Handle all message types from server

### Example Usage

```javascript
const client = new VoiceChatClient("ws://localhost:8000/api/v1/voice/ws");

// Set up handlers
client.onTranscription = (text) => console.log("You said:", text);
client.onResponseText = (text) => console.log("AI says:", text);
client.onAudioChunk = (chunk) => playAudioChunk(chunk);

// Connect (system prompt and voice are configured on backend)
await client.connect();

// Start recording when button pressed
startRecording(); // Captures and sends audio chunks

// Stop recording when button released
stopRecording(); // Sends audio_end message

// Close when done
client.close();
```

## Testing

### Test with curl (WebSocket)

You can use `websocat` or similar tools to test:

```bash
# Install websocat
cargo install websocat

# Connect
websocat ws://localhost:8000/api/v1/voice/ws

# Send start session message
{"type":"start_session","session_id":"test123"}
```

### Test with Python

```python
import asyncio
import websockets
import json
import base64

async def test_voice_chat():
    uri = "ws://localhost:8000/api/v1/voice/ws"

      async with websockets.connect(uri) as ws:
        # Start session
        await ws.send(json.dumps({
            "type": "start_session",
            "session_id": "test123"
        }))

        response = await ws.recv()
        print("Response:", response)

        # Read an audio file
        with open("test_audio.wav", "rb") as f:
            audio_data = f.read()

        # Send audio
        await ws.send(json.dumps({
            "type": "audio_chunk",
            "session_id": "test123",
            "audio_data": base64.b64encode(audio_data).decode(),
            "format": "wav"
        }))

        # End audio
        await ws.send(json.dumps({
            "type": "audio_end",
            "session_id": "test123"
        }))

        # Receive responses
        while True:
            response = await ws.recv()
            data = json.loads(response)
            print(f"Received: {data['type']}")

            if data['type'] == 'audio_stream_end':
                break

        # End session
        await ws.send(json.dumps({
            "type": "end_session",
            "session_id": "test123"
        }))

asyncio.run(test_voice_chat())
```

## Error Handling

The server will send error messages in the following format:

```json
{
  "type": "error",
  "session_id": "session_id",
  "error": "detailed error message",
  "code": "error_code"
}
```

### Common Error Codes

- `session_start_error`: Failed to start session
- `audio_chunk_error`: Error processing audio chunk
- `audio_processing_error`: Error during transcription, generation, or TTS
- `session_end_error`: Error ending session
- `unknown_message_type`: Invalid message type received
- `websocket_error`: General WebSocket error
- `invalid_first_message`: First message was not START_SESSION

## Conversation History

The backend maintains conversation history per session. This allows for contextual responses across multiple turns in the conversation.

The history includes:

- System prompt (from backend configuration)
- User messages (from transcriptions)
- Assistant responses

History is automatically cleared when the session ends.

## Limitations & Future Improvements

### Current Limitations

1. No authentication/authorization on WebSocket endpoint
2. No rate limiting
3. No subscription tier checks
4. Audio buffering in memory (not suitable for very long sessions)
5. No session persistence (history lost if server restarts)

### Future Improvements

1. Add Auth0 token authentication for WebSocket connections
2. Implement rate limiting per user
3. Add subscription tier checks (free, community, pro)
4. Use proper audio streaming without full buffering
5. Add session persistence with database storage
6. Add voice activity detection (VAD) for automatic speech detection
7. Support multiple concurrent sessions per user
8. Add audio quality selection
9. Add language selection for transcription
10. Add real-time partial transcription (streaming STT)

## Files Structure

```
├── clients/
│   └── openai_client.py          # OpenAI API client wrapper
├── services/
│   └── voice_chat_service.py     # Voice chat orchestration service
├── schemas/
│   └── voice_chat.py             # Pydantic schemas for messages
├── api/
│   └── routes/
│       └── voice_chat.py         # WebSocket endpoint
└── examples/
    ├── voice_chat_client_example.js  # Electron client example
    └── VOICE_CHAT_README.md         # This file
```

## Production Considerations

Before deploying to production:

1. **Security**:

   - Add WebSocket authentication
   - Validate audio size limits
   - Implement rate limiting
   - Add CORS restrictions

2. **Scalability**:

   - Consider using a message queue for audio processing
   - Implement connection pooling
   - Add load balancing for multiple backend instances
   - Use Redis for session state if running multiple servers

3. **Monitoring**:

   - Log all sessions and errors
   - Monitor WebSocket connection counts
   - Track API usage and costs
   - Set up alerts for errors

4. **Cost Management**:
   - Monitor OpenAI API costs
   - Implement usage quotas per user/tier
   - Consider caching common responses

## Support

For issues or questions, please refer to:

- OpenAI API Documentation: https://platform.openai.com/docs
- FastAPI WebSocket Documentation: https://fastapi.tiangolo.com/advanced/websockets/
