# Authentication Guide

## Overview

The AI Nutritionist API uses JWT (JSON Web Token) based authentication for secure access to all endpoints. This guide covers the complete authentication flow, token management, and security best practices.

## Authentication Flow

### 1. Initiate Authentication

Start the authentication process by requesting a verification code:

```bash
curl -X POST https://api.ai-nutritionist.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "sms",
    "identifier": "+1234567890"
  }'
```

**Response:**

```json
{
  "message": "Verification code sent",
  "expires_in": 300
}
```

### 2. Verify Code and Get Tokens

Complete authentication with the verification code:

```bash
curl -X POST https://api.ai-nutritionist.com/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "+1234567890",
    "code": "123456"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user": {
    "id": "user_123456",
    "email": "user@example.com",
    "phone": "+1234567890",
    "subscription_tier": "premium"
  }
}
```

### 3. Use Access Token

Include the access token in the Authorization header for all API requests:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     https://api.ai-nutritionist.com/v1/plan/generate
```

### 4. Refresh Tokens

When the access token expires, use the refresh token to get a new one:

```bash
curl -X POST https://api.ai-nutritionist.com/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

## Authentication Methods

### SMS Authentication

Send verification codes via SMS:

```javascript
const response = await fetch("/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    channel: "sms",
    identifier: "+1234567890",
  }),
});
```

### Email Authentication

Send magic links via email:

```javascript
const response = await fetch("/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    channel: "email",
    identifier: "user@example.com",
  }),
});
```

## Token Management

### Access Token Structure

JWT access tokens contain user information and permissions:

```json
{
  "sub": "user_123456",
  "email": "user@example.com",
  "phone": "+1234567890",
  "subscription_tier": "premium",
  "permissions": ["read:plans", "write:plans", "read:analytics"],
  "iat": 1697203800,
  "exp": 1697207400
}
```

### Token Lifecycle

| Token Type        | Lifetime  | Purpose        |
| ----------------- | --------- | -------------- |
| Access Token      | 1 hour    | API access     |
| Refresh Token     | 30 days   | Token renewal  |
| Verification Code | 5 minutes | Authentication |

### Automatic Token Refresh

Implement automatic token refresh in your application:

```javascript
class APIClient {
  constructor(accessToken, refreshToken) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  async request(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.accessToken}`,
        ...options.headers,
      },
    });

    if (response.status === 401) {
      // Token expired, refresh it
      await this.refreshAccessToken();

      // Retry original request
      return fetch(url, {
        ...options,
        headers: {
          Authorization: `Bearer ${this.accessToken}`,
          ...options.headers,
        },
      });
    }

    return response;
  }

  async refreshAccessToken() {
    const response = await fetch("/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        refresh_token: this.refreshToken,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      this.accessToken = data.access_token;
    } else {
      // Refresh failed, redirect to login
      window.location.href = "/login";
    }
  }
}
```

## Error Handling

### Common Authentication Errors

| Status Code | Error Type            | Description             | Action           |
| ----------- | --------------------- | ----------------------- | ---------------- |
| 400         | `validation_error`    | Invalid request format  | Fix request body |
| 401         | `invalid_code`        | Wrong verification code | Request new code |
| 401         | `expired_token`       | Token has expired       | Refresh token    |
| 401         | `invalid_token`       | Token is malformed      | Re-authenticate  |
| 429         | `rate_limit_exceeded` | Too many requests       | Wait and retry   |

### Error Response Format

```json
{
  "type": "https://api.ai-nutritionist.com/problems/invalid-token",
  "title": "Invalid Token",
  "status": 401,
  "detail": "The provided access token is invalid or expired",
  "instance": "/v1/plan/generate"
}
```

## Security Best Practices

### Token Storage

**✅ Do:**

- Store tokens securely (encrypted storage, secure cookies)
- Use HTTPS for all communications
- Implement automatic token refresh
- Clear tokens on logout

**❌ Don't:**

- Store tokens in localStorage (XSS risk)
- Log tokens in application logs
- Send tokens in URL parameters
- Share tokens between applications

### Client-Side Implementation

**Secure Token Storage (React Native):**

```javascript
import { Keychain } from "react-native-keychain";

export class SecureTokenStorage {
  static async storeTokens(accessToken, refreshToken) {
    await Keychain.setInternetCredentials(
      "ai-nutritionist-tokens",
      accessToken,
      refreshToken
    );
  }

  static async getTokens() {
    try {
      const credentials = await Keychain.getInternetCredentials(
        "ai-nutritionist-tokens"
      );
      return {
        accessToken: credentials.username,
        refreshToken: credentials.password,
      };
    } catch (error) {
      return null;
    }
  }

  static async clearTokens() {
    await Keychain.resetInternetCredentials("ai-nutritionist-tokens");
  }
}
```

**Secure Token Storage (Web):**

```javascript
// Use secure, httpOnly cookies for token storage
export class TokenManager {
  static async authenticate(identifier, code) {
    const response = await fetch("/v1/auth/verify", {
      method: "POST",
      credentials: "include", // Include cookies
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, code }),
    });

    if (response.ok) {
      // Tokens are automatically stored in secure cookies
      return response.json();
    }

    throw new Error("Authentication failed");
  }

  static async makeAuthenticatedRequest(url, options = {}) {
    return fetch(url, {
      ...options,
      credentials: "include", // Include auth cookies
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  }
}
```

### Server-Side Implementation

**Express.js Middleware:**

```javascript
const jwt = require("jsonwebtoken");

function authenticateToken(req, res, next) {
  const authHeader = req.headers["authorization"];
  const token = authHeader && authHeader.split(" ")[1];

  if (!token) {
    return res.status(401).json({
      type: "https://api.ai-nutritionist.com/problems/missing-token",
      title: "Missing Token",
      status: 401,
      detail: "Access token is required",
    });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({
        type: "https://api.ai-nutritionist.com/problems/invalid-token",
        title: "Invalid Token",
        status: 403,
        detail: "Access token is invalid or expired",
      });
    }

    req.user = user;
    next();
  });
}

// Usage
app.get("/v1/plan/generate", authenticateToken, (req, res) => {
  // Protected route logic
});
```

## Multi-Factor Authentication

### TOTP (Time-based One-Time Password)

For enhanced security, enable TOTP-based 2FA:

```bash
# Enable TOTP for user
curl -X POST https://api.ai-nutritionist.com/v1/auth/totp/enable \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response:**

```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "secret": "JBSWY3DPEHPK3PXP",
  "backup_codes": ["12345678", "87654321", "11223344"]
}
```

### Verify TOTP Code

```bash
curl -X POST https://api.ai-nutritionist.com/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "+1234567890",
    "code": "123456",
    "totp_code": "654321"
  }'
```

## Testing Authentication

### Unit Tests

```javascript
describe("Authentication", () => {
  test("should authenticate with valid credentials", async () => {
    const response = await request(app)
      .post("/v1/auth/verify")
      .send({
        identifier: "+1234567890",
        code: "123456",
      })
      .expect(200);

    expect(response.body).toHaveProperty("access_token");
    expect(response.body).toHaveProperty("refresh_token");
  });

  test("should reject invalid verification code", async () => {
    await request(app)
      .post("/v1/auth/verify")
      .send({
        identifier: "+1234567890",
        code: "invalid",
      })
      .expect(401);
  });
});
```

### Integration Tests

```bash
# Test authentication flow
./test-auth.sh

# Expected output:
# ✅ Login request successful
# ✅ Verification successful
# ✅ Token refresh successful
# ✅ Protected endpoint accessible
```

## Troubleshooting

### Common Issues

**Q: My tokens keep expiring quickly**
A: Check your system clock. JWT tokens are time-sensitive.

**Q: Getting 401 errors with valid token**
A: Verify the token format and ensure you're including the "Bearer " prefix.

**Q: Refresh token not working**
A: Refresh tokens are single-use. Store the new refresh token from the response.

**Q: Can't receive SMS codes**
A: Check phone number format (E.164) and carrier compatibility.

### Debug Mode

Enable debug logging to troubleshoot authentication issues:

```javascript
const client = new APIClient({
  debug: true,
  onTokenRefresh: (newToken) => {
    console.log("Token refreshed:", newToken);
  },
  onAuthError: (error) => {
    console.error("Auth error:", error);
  },
});
```

## Rate Limiting

Authentication endpoints have specific rate limits:

| Endpoint        | Rate Limit | Burst Limit |
| --------------- | ---------- | ----------- |
| `/auth/login`   | 5/minute   | 10          |
| `/auth/verify`  | 10/minute  | 20          |
| `/auth/refresh` | 20/minute  | 50          |

Implement exponential backoff for rate-limited requests:

```javascript
async function authenticateWithBackoff(identifier, code, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await authenticate(identifier, code);
    } catch (error) {
      if (error.status === 429 && attempt < maxRetries) {
        const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
        await new Promise((resolve) => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
}
```
