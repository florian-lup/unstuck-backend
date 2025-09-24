# Gaming Search Engine API - Client Implementation Guide

## Overview

This guide provides comprehensive instructions for implementing the Gaming Search Engine API in your Electron application with Auth0 JWT authentication.

## Table of Contents

- [Authentication Setup](#authentication-setup)
- [API Client Implementation](#api-client-implementation)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Security Best Practices](#security-best-practices)
- [Examples](#examples)

## Authentication Setup

### 1. Auth0 Configuration

First, configure Auth0 in your Electron app:

```typescript
// auth0-config.ts
export const auth0Config = {
  domain: "your-domain.auth0.com",
  clientId: "your-client-id",
  audience: "https://your-gaming-search-api/", // Must match backend AUTH0_API_AUDIENCE
  scope: "openid profile email gaming:search gaming:history",
  redirectUri: "http://localhost:3000/callback", // Adjust for your app
};
```

### 2. Install Dependencies

```bash
npm install @auth0/auth0-spa-js axios
# or
yarn add @auth0/auth0-spa-js axios
```

### 3. Auth0 Service Implementation

```typescript
// services/auth.service.ts
import { Auth0Client, User } from "@auth0/auth0-spa-js";
import { auth0Config } from "../config/auth0-config";

class AuthService {
  private auth0Client: Auth0Client;

  constructor() {
    this.auth0Client = new Auth0Client({
      domain: auth0Config.domain,
      clientId: auth0Config.clientId,
      authorizationParams: {
        audience: auth0Config.audience,
        scope: auth0Config.scope,
        redirect_uri: auth0Config.redirectUri,
      },
    });
  }

  async initialize(): Promise<void> {
    await this.auth0Client.checkSession();
  }

  async login(): Promise<void> {
    await this.auth0Client.loginWithRedirect();
  }

  async handleRedirectCallback(): Promise<void> {
    await this.auth0Client.handleRedirectCallback();
  }

  async logout(): Promise<void> {
    await this.auth0Client.logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    });
  }

  async getAccessToken(): Promise<string | null> {
    try {
      const token = await this.auth0Client.getTokenSilently();
      return token;
    } catch (error) {
      console.error("Error getting access token:", error);
      return null;
    }
  }

  async isAuthenticated(): Promise<boolean> {
    return await this.auth0Client.isAuthenticated();
  }

  async getUser(): Promise<User | undefined> {
    return await this.auth0Client.getUser();
  }
}

export const authService = new AuthService();
```

## API Client Implementation

### 1. Base API Client

```typescript
// services/api.client.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { authService } from "./auth.service";

class APIClient {
  private client: AxiosInstance;
  private baseURL = "http://localhost:8000/api/v1"; // Change for production

  constructor() {
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        const token = await authService.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      async (error) => {
        const originalRequest = error.config;

        // Handle 401 Unauthorized - token expired
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Try to get a new token
            const newToken = await authService.getAccessToken();
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Redirect to login if token refresh fails
            await authService.login();
            return Promise.reject(refreshError);
          }
        }

        // Handle rate limiting
        if (error.response?.status === 429) {
          const retryAfter = error.response.headers["retry-after"];
          if (retryAfter) {
            // Show user-friendly message about rate limiting
            throw new APIError(
              "rate_limit_exceeded",
              `Too many requests. Please wait ${retryAfter} seconds.`,
              429
            );
          }
        }

        throw this.handleError(error);
      }
    );
  }

  private handleError(error: any): APIError {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      return new APIError(
        data.error || "api_error",
        data.description || data.message || "An error occurred",
        status
      );
    } else if (error.request) {
      // Network error
      return new APIError(
        "network_error",
        "Unable to connect to the server",
        0
      );
    } else {
      // Other error
      return new APIError(
        "unknown_error",
        error.message || "An unknown error occurred",
        0
      );
    }
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }
}

class APIError extends Error {
  constructor(public code: string, message: string, public statusCode: number) {
    super(message);
    this.name = "APIError";
  }
}

export { APIClient, APIError };
export const apiClient = new APIClient();
```

### 2. Gaming Search Service

```typescript
// services/gaming-search.service.ts
import { apiClient } from "./api.client";

export interface GamingSearchRequest {
  query: string;
  conversation_id?: string;
  conversation_history?: ConversationMessage[];
}

export interface ConversationMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface GamingSearchResponse {
  id: string;
  conversation_id: string;
  model: string;
  created: number;
  content: string;
  search_results?: SearchResult[];
  usage?: UsageStats;
  finish_reason?: string;
}

export interface SearchResult {
  title: string;
  url: string;
  date?: string;
}

export interface UsageStats {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  search_context_size?: string;
  citation_tokens?: number;
  num_search_queries?: number;
}

export interface UserInfo {
  user: {
    user_id: string;
    email?: string;
    name?: string;
    permissions: string[];
  };
  conversation_count: number;
  last_activity?: number;
}

class GamingSearchService {
  async search(request: GamingSearchRequest): Promise<GamingSearchResponse> {
    return await apiClient.post<GamingSearchResponse>(
      "/gaming/search",
      request
    );
  }

  async getConversationHistory(
    conversationId: string
  ): Promise<ConversationMessage[]> {
    const response = await apiClient.get<{ messages: ConversationMessage[] }>(
      `/gaming/conversations/${conversationId}/history`
    );
    return response.messages;
  }

  async clearConversation(
    conversationId: string
  ): Promise<{ success: boolean }> {
    return await apiClient.delete<{ success: boolean }>(
      `/gaming/conversations/${conversationId}`
    );
  }

  async listConversations(): Promise<{
    conversations: string[];
    total: number;
  }> {
    return await apiClient.get<{ conversations: string[]; total: number }>(
      "/gaming/conversations"
    );
  }

  async getUserInfo(): Promise<UserInfo> {
    return await apiClient.get<UserInfo>("/auth/me");
  }

  async verifyToken(): Promise<{ valid: boolean; user_id: string }> {
    return await apiClient.post<{ valid: boolean; user_id: string }>(
      "/auth/verify"
    );
  }

  // Public search (no authentication required)
  async publicSearch(
    request: GamingSearchRequest
  ): Promise<GamingSearchResponse> {
    return await apiClient.post<GamingSearchResponse>(
      "/gaming/search/public",
      request
    );
  }
}

export const gamingSearchService = new GamingSearchService();
```

## Error Handling

### 1. Error Types and Handling

```typescript
// utils/error-handler.ts
import { APIError } from "../services/api.client";

export interface ErrorInfo {
  type: "auth" | "network" | "rate_limit" | "validation" | "server" | "unknown";
  message: string;
  code?: string;
  retryable: boolean;
}

export function handleAPIError(error: APIError): ErrorInfo {
  switch (error.code) {
    case "token_expired":
    case "invalid_token":
    case "invalid_signature":
      return {
        type: "auth",
        message: "Authentication failed. Please log in again.",
        code: error.code,
        retryable: false,
      };

    case "rate_limit_exceeded":
      return {
        type: "rate_limit",
        message: "Too many requests. Please wait a moment before trying again.",
        code: error.code,
        retryable: true,
      };

    case "validation_error":
      return {
        type: "validation",
        message: "Invalid request data. Please check your input.",
        code: error.code,
        retryable: false,
      };

    case "network_error":
      return {
        type: "network",
        message:
          "Unable to connect to the server. Please check your internet connection.",
        code: error.code,
        retryable: true,
      };

    case "internal_server_error":
      return {
        type: "server",
        message: "Server error occurred. Please try again later.",
        code: error.code,
        retryable: true,
      };

    default:
      return {
        type: "unknown",
        message: error.message || "An unexpected error occurred.",
        code: error.code,
        retryable: false,
      };
  }
}

// Error retry utility
export async function retryOperation<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;

      if (error instanceof APIError) {
        const errorInfo = handleAPIError(error);
        if (!errorInfo.retryable || attempt === maxRetries) {
          throw error;
        }
      }

      if (attempt < maxRetries) {
        await new Promise((resolve) => setTimeout(resolve, delay * attempt));
      }
    }
  }

  throw lastError!;
}
```

## Rate Limiting

### 1. Rate Limit Handling

```typescript
// utils/rate-limit.ts
export class RateLimitManager {
  private rateLimitInfo: Map<string, RateLimitInfo> = new Map();

  updateRateLimit(headers: any): void {
    const remaining = parseInt(headers["x-ratelimit-remaining"] || "0");
    const limit = parseInt(headers["x-ratelimit-limit"] || "100");
    const reset = parseInt(headers["x-ratelimit-reset"] || "0");

    this.rateLimitInfo.set("global", {
      remaining,
      limit,
      reset,
      percentage: (remaining / limit) * 100,
    });
  }

  getRateLimitInfo(): RateLimitInfo | null {
    return this.rateLimitInfo.get("global") || null;
  }

  shouldShowWarning(): boolean {
    const info = this.getRateLimitInfo();
    return info ? info.percentage < 20 : false;
  }

  getTimeUntilReset(): number {
    const info = this.getRateLimitInfo();
    if (!info) return 0;

    return Math.max(0, info.reset - Math.floor(Date.now() / 1000));
  }
}

interface RateLimitInfo {
  remaining: number;
  limit: number;
  reset: number;
  percentage: number;
}

export const rateLimitManager = new RateLimitManager();
```

## Security Best Practices

### 1. Token Storage (Electron-specific)

```typescript
// services/secure-storage.ts
import { safeStorage } from "electron";

class SecureStorage {
  private readonly TOKEN_KEY = "auth_tokens";

  async storeTokens(tokens: {
    access_token: string;
    refresh_token?: string;
  }): Promise<void> {
    try {
      const encrypted = safeStorage.encryptString(JSON.stringify(tokens));
      localStorage.setItem(this.TOKEN_KEY, encrypted.toString("base64"));
    } catch (error) {
      console.error("Failed to store tokens securely:", error);
      // Fallback to memory storage or session storage
    }
  }

  async getTokens(): Promise<{
    access_token: string;
    refresh_token?: string;
  } | null> {
    try {
      const encrypted = localStorage.getItem(this.TOKEN_KEY);
      if (!encrypted) return null;

      const buffer = Buffer.from(encrypted, "base64");
      const decrypted = safeStorage.decryptString(buffer);
      return JSON.parse(decrypted);
    } catch (error) {
      console.error("Failed to retrieve tokens:", error);
      return null;
    }
  }

  async clearTokens(): Promise<void> {
    localStorage.removeItem(this.TOKEN_KEY);
  }
}

export const secureStorage = new SecureStorage();
```

### 2. Request Security

```typescript
// utils/security.ts
export function sanitizeInput(input: string): string {
  // Remove potentially dangerous characters
  return input
    .replace(/[<>]/g, "") // Remove HTML tags
    .replace(/javascript:/gi, "") // Remove javascript: URLs
    .trim();
}

export function validateSearchQuery(query: string): {
  valid: boolean;
  message?: string;
} {
  if (!query || query.trim().length === 0) {
    return { valid: false, message: "Search query cannot be empty" };
  }

  if (query.length > 500) {
    return {
      valid: false,
      message: "Search query is too long (max 500 characters)",
    };
  }

  // Check for suspicious patterns
  const suspiciousPatterns = [
    /script\s*:/i,
    /javascript\s*:/i,
    /data\s*:/i,
    /vbscript\s*:/i,
  ];

  if (suspiciousPatterns.some((pattern) => pattern.test(query))) {
    return { valid: false, message: "Invalid characters in search query" };
  }

  return { valid: true };
}
```

## Examples

### 1. React Component Example

```tsx
// components/GamingSearch.tsx
import React, { useState, useEffect } from "react";
import {
  gamingSearchService,
  GamingSearchRequest,
  GamingSearchResponse,
} from "../services/gaming-search.service";
import { handleAPIError, retryOperation } from "../utils/error-handler";
import { validateSearchQuery } from "../utils/security";
import { rateLimitManager } from "../utils/rate-limit";

const GamingSearch: React.FC = () => {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<GamingSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string>("");

  const handleSearch = async () => {
    // Validate input
    const validation = validateSearchQuery(query);
    if (!validation.valid) {
      setError(validation.message || "Invalid query");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const searchRequest: GamingSearchRequest = {
        query: query.trim(),
        conversation_id: conversationId || undefined,
      };

      // Use retry logic for resilient requests
      const result = await retryOperation(() =>
        gamingSearchService.search(searchRequest)
      );

      setResponse(result);
      setConversationId(result.conversation_id);

      // Update rate limit info from response headers
      // (This would be handled in the API client interceptor)
    } catch (err: any) {
      const errorInfo = handleAPIError(err);
      setError(errorInfo.message);

      // Handle specific error types
      if (errorInfo.type === "auth") {
        // Redirect to login
        window.location.href = "/login";
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gaming-search">
      <div className="search-input">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about any game..."
          maxLength={500}
          disabled={loading}
        />
        <button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {response && (
        <div className="search-results">
          <div className="response-content">{response.content}</div>

          {response.search_results && response.search_results.length > 0 && (
            <div className="sources">
              <h4>Sources:</h4>
              <ul>
                {response.search_results.map((result, index) => (
                  <li key={index}>
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {result.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Rate limit warning */}
      {rateLimitManager.shouldShowWarning() && (
        <div className="rate-limit-warning">
          ⚠️ You're approaching the rate limit.
          {rateLimitManager.getRateLimitInfo()?.remaining} requests remaining.
        </div>
      )}
    </div>
  );
};

export default GamingSearch;
```

### 2. Conversation Management

```tsx
// components/ConversationManager.tsx
import React, { useState, useEffect } from "react";
import { gamingSearchService } from "../services/gaming-search.service";

const ConversationManager: React.FC = () => {
  const [conversations, setConversations] = useState<string[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string>("");

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const result = await gamingSearchService.listConversations();
      setConversations(result.conversations);
    } catch (error) {
      console.error("Failed to load conversations:", error);
    }
  };

  const clearConversation = async (conversationId: string) => {
    try {
      await gamingSearchService.clearConversation(conversationId);
      setConversations(conversations.filter((id) => id !== conversationId));
      if (selectedConversation === conversationId) {
        setSelectedConversation("");
      }
    } catch (error) {
      console.error("Failed to clear conversation:", error);
    }
  };

  return (
    <div className="conversation-manager">
      <h3>Your Conversations</h3>

      {conversations.length === 0 ? (
        <p>No conversations yet. Start searching to begin!</p>
      ) : (
        <ul>
          {conversations.map((conversationId) => (
            <li key={conversationId}>
              <span
                onClick={() => setSelectedConversation(conversationId)}
                className={
                  selectedConversation === conversationId ? "selected" : ""
                }
              >
                {conversationId.slice(0, 8)}...
              </span>
              <button
                onClick={() => clearConversation(conversationId)}
                className="delete-btn"
              >
                🗑️
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ConversationManager;
```

## Environment Setup

Create a `.env` file in your project root:

```bash
# Application Settings
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Auth0 Configuration (Required)
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_AUDIENCE=https://your-gaming-search-api/

# Perplexity AI API (Required)
PERPLEXITY_API_KEY=your-perplexity-api-key

# Redis (Optional)
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Security
SECRET_KEY=your-super-secret-key-256-bits
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Testing

### 1. Testing Authentication

```typescript
// tests/auth.test.ts
describe("Authentication", () => {
  test("should authenticate user and get token", async () => {
    const isAuthenticated = await authService.isAuthenticated();
    expect(isAuthenticated).toBe(true);

    const token = await authService.getAccessToken();
    expect(token).toBeDefined();
  });
});
```

### 2. Testing API Calls

```typescript
// tests/gaming-search.test.ts
describe("Gaming Search API", () => {
  test("should perform search successfully", async () => {
    const request = {
      query: "What is the best strategy for Civilization VI?",
    };

    const response = await gamingSearchService.search(request);
    expect(response).toBeDefined();
    expect(response.content).toBeTruthy();
    expect(response.conversation_id).toBeTruthy();
  });

  test("should handle rate limiting", async () => {
    // Test rate limiting behavior
    const promises = Array(150)
      .fill(0)
      .map(() => gamingSearchService.search({ query: "test" }));

    await expect(Promise.all(promises)).rejects.toThrow("rate_limit_exceeded");
  });
});
```

## Production Deployment

### 1. Backend Deployment

```bash
# Install dependencies
poetry install --no-dev

# Run migrations (if using database)
# alembic upgrade head

# Start production server
poetry run python main.py

# Or use gunicorn for production
poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.app:app --bind 0.0.0.0:8000
```

### 2. Environment Variables

Ensure these environment variables are set in production:

- `AUTH0_DOMAIN`
- `AUTH0_API_AUDIENCE`
- `PERPLEXITY_API_KEY`
- `SECRET_KEY` (generate a secure random key)
- `REDIS_URL` (if using Redis)
- `DEBUG=false`

### 3. Security Checklist

- ✅ Use HTTPS in production
- ✅ Set secure environment variables
- ✅ Configure CORS properly
- ✅ Enable rate limiting
- ✅ Use secure token storage in Electron
- ✅ Validate all inputs
- ✅ Handle errors gracefully
- ✅ Monitor API usage
- ✅ Implement logging

This comprehensive guide should help you implement the Gaming Search Engine API in your Electron application with proper Auth0 authentication, error handling, and security practices.
