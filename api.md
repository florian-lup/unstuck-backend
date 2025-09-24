You're absolutely right! Let me give you the **complete** request/response for the search endpoint:

## 🎯 **Complete Client API Call - Gaming Search**

### **What Your Client Sends**

**Endpoint:** `POST /api/v1/gaming/search`

**Headers:**

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Content-Type: application/json
```

**Body:**

```json
{
  "query": "What's the best strategy for Civilization VI?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Notes:**

- `conversation_id` is **optional** - omit for new conversations
- `query` is **required** (1-500 characters)

### **What You Receive Back**

**Status:** `200 OK`

**Headers:**

```
X-Request-ID: 1703123456789
X-Process-Time: 2.3456
X-RateLimit-Remaining: 95
```

**Body:**

```json
{
  "id": "resp_abc123",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "model": "llama-3.1-sonar-large-online",
  "created": 1703123456,
  "content": "Here are the best strategies for Civilization VI: 1) Early expansion is crucial...",
  "search_results": [
    {
      "title": "Civilization VI Strategy Guide",
      "url": "https://example.com/civ6-guide",
      "date": "2024-01-15"
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 300,
    "total_tokens": 450
  },
  "finish_reason": "stop"
}
```

### **Error Response (if something goes wrong)**

**Status:** `4xx` or `5xx`

**Body:**

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Try again in 30 seconds.",
  "request_id": "1703123456789"
}
```

**That's the complete request/response!** 🎯

**Key point:** JWT goes in `Authorization` header, **not** in the body.

Keys Your Client Needs:
Auth0 Domain - your-domain.auth0.com
Auth0 Client ID - From your Auth0 dashboard
Railway URL - Your deployed API endpoint
