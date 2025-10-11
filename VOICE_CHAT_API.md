# Voice Chat WebSocket API

## Connection

**Endpoint:** `wss://unstuck-backend-production-d9c1.up.railway.app/api/v1/voice/ws`

Connect using a standard WebSocket client. The connection must be established before any messages are sent.

**Note:** Use `wss://` (secure WebSocket) for production

## Message Flow

### 1. Session Initialization

**Client sends:**

```json
{
  "type": "start_session",
  "session_id": "unique-session-id"
}
```

**Server responds:**

```json
{
  "type": "session_started",
  "session_id": "unique-session-id"
}
```

### 2. Audio Input (Repeatable)

**Client sends audio chunks:**

```json
{
  "type": "audio_chunk",
  "session_id": "unique-session-id",
  "audio_data": "base64-encoded-audio",
  "format": "wav"
}
```

**Client signals end of audio:**

```json
{
  "type": "audio_end",
  "session_id": "unique-session-id"
}
```

### 3. Server Processing & Response

**Server streams audio response:**

Start:

```json
{
  "type": "audio_stream_start",
  "session_id": "unique-session-id"
}
```

Chunks (multiple):

```json
{
  "type": "audio_stream_chunk",
  "session_id": "unique-session-id",
  "audio_data": "base64-encoded-audio-chunk"
}
```

End:

```json
{
  "type": "audio_stream_end",
  "session_id": "unique-session-id"
}
```

### 4. Session Termination

**Client sends:**

```json
{
  "type": "end_session",
  "session_id": "unique-session-id"
}
```

**Server responds:**

```json
{
  "type": "session_ended",
  "session_id": "unique-session-id"
}
```

## Error Handling

**Server error format:**

```json
{
  "type": "error",
  "session_id": "unique-session-id",
  "error": "error description",
  "code": "error_code"
}
```

## Client Implementation Notes

1. **First message must be `start_session`** - connection will be rejected otherwise
2. **Audio format:** WAV recommended for `audio_chunk` messages
3. **Audio encoding:** All audio data must be base64-encoded
4. **Chunking:** Split audio into manageable chunks (e.g., 100ms-1s each)
5. **Session persistence:** Conversation history is maintained per session
6. **Streaming:** Audio responses are streamed for low latency playback
7. **Cycle:** Steps 2-3 can repeat multiple times within one session

## Message Types Summary

**Client → Server:**

- `start_session` - Initialize conversation
- `audio_chunk` - Send audio data
- `audio_end` - Signal audio complete
- `end_session` - Close conversation

**Server → Client:**

- `session_started` - Confirmation
- `audio_stream_start` - Audio streaming begins
- `audio_stream_chunk` - Audio data chunk
- `audio_stream_end` - Audio streaming complete
- `session_ended` - Confirmation
- `error` - Error occurred
