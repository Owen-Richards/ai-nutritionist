# Rate Limiting Guide

## Overview

The AI Nutritionist API implements comprehensive rate limiting to ensure fair usage, prevent abuse, and maintain optimal performance for all users. This guide covers rate limiting policies, headers, error handling, and best practices.

## Rate Limiting Tiers

### Free Tier

- **API Calls**: 100 requests/hour
- **Burst Limit**: 10 requests/minute
- **Plan Generation**: 3 plans/day
- **Feedback Submissions**: 20/hour

### Premium Tier

- **API Calls**: 1,000 requests/hour
- **Burst Limit**: 50 requests/minute
- **Plan Generation**: 50 plans/day
- **Feedback Submissions**: 200/hour

### Enterprise Tier

- **API Calls**: 10,000 requests/hour
- **Burst Limit**: 200 requests/minute
- **Plan Generation**: Unlimited
- **Feedback Submissions**: Unlimited

## Rate Limit Headers

Every API response includes rate limiting headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1697207400
X-RateLimit-Retry-After: 3600
X-RateLimit-Type: user
```

### Header Descriptions

| Header                    | Description                                           |
| ------------------------- | ----------------------------------------------------- |
| `X-RateLimit-Limit`       | Maximum requests allowed in the current window        |
| `X-RateLimit-Remaining`   | Requests remaining in the current window              |
| `X-RateLimit-Reset`       | Unix timestamp when the limit resets                  |
| `X-RateLimit-Retry-After` | Seconds to wait before making another request         |
| `X-RateLimit-Type`        | Type of rate limit applied (`user`, `ip`, `endpoint`) |

## Rate Limiting Strategies

### 1. Token Bucket Algorithm

Most endpoints use a token bucket algorithm:

```javascript
// Simplified token bucket implementation
class TokenBucket {
  constructor(capacity, refillRate) {
    this.capacity = capacity;
    this.tokens = capacity;
    this.refillRate = refillRate; // tokens per second
    this.lastRefill = Date.now();
  }

  consume(tokens = 1) {
    this.refill();

    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return true;
    }

    return false;
  }

  refill() {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    const tokensToAdd = elapsed * this.refillRate;

    this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
}
```

### 2. Sliding Window

Critical endpoints use sliding window rate limiting:

```javascript
class SlidingWindow {
  constructor(windowSize, maxRequests) {
    this.windowSize = windowSize * 1000; // Convert to milliseconds
    this.maxRequests = maxRequests;
    this.requests = [];
  }

  isAllowed() {
    const now = Date.now();
    const windowStart = now - this.windowSize;

    // Remove old requests
    this.requests = this.requests.filter((time) => time > windowStart);

    if (this.requests.length < this.maxRequests) {
      this.requests.push(now);
      return true;
    }

    return false;
  }
}
```

## Endpoint-Specific Limits

### Authentication Endpoints

```http
POST /v1/auth/login
Rate Limit: 5 requests/minute per IP
Burst: 10 requests

POST /v1/auth/verify
Rate Limit: 10 requests/minute per IP
Burst: 20 requests
```

### Meal Planning Endpoints

```http
POST /v1/plan/generate
Rate Limit: Based on subscription tier
Additional: AI processing queue limits

GET /v1/plan/{plan_id}
Rate Limit: 100 requests/hour per user
Burst: 20 requests/minute
```

### Community Endpoints

```http
POST /v1/community/reflections
Rate Limit: 5 submissions/hour per user
Additional: Content moderation delays

POST /v1/community/crews/join
Rate Limit: 3 joins/day per user
```

### Analytics Endpoints

```http
POST /v1/analytics/events
Rate Limit: 1000 events/hour per user
Burst: 100 events/minute

GET /v1/analytics/dashboard
Rate Limit: 10 requests/hour per user
```

## Error Responses

### Rate Limit Exceeded (429)

```json
{
  "type": "https://api.ai-nutritionist.com/problems/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests. Please try again later.",
  "instance": "/v1/plan/generate",
  "retry_after": 3600,
  "limits": {
    "current": 100,
    "maximum": 100,
    "reset_time": "2024-10-13T16:30:00Z"
  }
}
```

### Rate Limit Headers in Error Response

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1697207400
Retry-After: 3600
Content-Type: application/json
```

## Client Implementation

### Basic Rate Limit Handling

```javascript
class RateLimitedClient {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
    this.rateLimitInfo = {};
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          Authorization: `Bearer ${this.token}`,
          "Content-Type": "application/json",
          ...options.headers,
        },
      });

      // Update rate limit info from headers
      this.updateRateLimitInfo(response.headers);

      if (response.status === 429) {
        const retryAfter = response.headers.get("Retry-After");
        throw new RateLimitError(retryAfter);
      }

      return response;
    } catch (error) {
      if (error instanceof RateLimitError) {
        // Handle rate limiting
        await this.handleRateLimit(error.retryAfter);
        return this.request(endpoint, options); // Retry
      }
      throw error;
    }
  }

  updateRateLimitInfo(headers) {
    this.rateLimitInfo = {
      limit: parseInt(headers.get("X-RateLimit-Limit")),
      remaining: parseInt(headers.get("X-RateLimit-Remaining")),
      reset: parseInt(headers.get("X-RateLimit-Reset")),
      retryAfter: parseInt(headers.get("X-RateLimit-Retry-After")),
    };
  }

  async handleRateLimit(retryAfter) {
    console.log(`Rate limited. Waiting ${retryAfter} seconds...`);
    await new Promise((resolve) => setTimeout(resolve, retryAfter * 1000));
  }

  getRemainingRequests() {
    return this.rateLimitInfo.remaining || 0;
  }

  getResetTime() {
    return new Date(this.rateLimitInfo.reset * 1000);
  }
}

class RateLimitError extends Error {
  constructor(retryAfter) {
    super("Rate limit exceeded");
    this.retryAfter = retryAfter;
  }
}
```

### Advanced Rate Limit Handling with Exponential Backoff

```javascript
class AdvancedRateLimitClient {
  constructor(baseURL, token, options = {}) {
    this.baseURL = baseURL;
    this.token = token;
    this.maxRetries = options.maxRetries || 3;
    this.baseDelay = options.baseDelay || 1000;
    this.maxDelay = options.maxDelay || 60000;
    this.jitter = options.jitter || true;
  }

  async requestWithRetry(endpoint, options = {}, retryCount = 0) {
    try {
      return await this.request(endpoint, options);
    } catch (error) {
      if (error instanceof RateLimitError && retryCount < this.maxRetries) {
        const delay = this.calculateDelay(retryCount, error.retryAfter);
        console.log(
          `Retry ${retryCount + 1}/${this.maxRetries} after ${delay}ms`
        );

        await new Promise((resolve) => setTimeout(resolve, delay));
        return this.requestWithRetry(endpoint, options, retryCount + 1);
      }
      throw error;
    }
  }

  calculateDelay(retryCount, retryAfter = null) {
    if (retryAfter) {
      return retryAfter * 1000; // Use server-provided delay
    }

    // Exponential backoff with jitter
    let delay = Math.min(
      this.baseDelay * Math.pow(2, retryCount),
      this.maxDelay
    );

    if (this.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5); // Add 0-50% jitter
    }

    return Math.floor(delay);
  }
}
```

### Proactive Rate Limit Management

```javascript
class ProactiveRateLimitClient extends RateLimitedClient {
  constructor(baseURL, token) {
    super(baseURL, token);
    this.requestQueue = [];
    this.processing = false;
  }

  async queuedRequest(endpoint, options = {}) {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({
        endpoint,
        options,
        resolve,
        reject,
      });

      this.processQueue();
    });
  }

  async processQueue() {
    if (this.processing || this.requestQueue.length === 0) {
      return;
    }

    this.processing = true;

    while (this.requestQueue.length > 0) {
      // Check if we have remaining requests
      if (this.rateLimitInfo.remaining <= 0) {
        const resetTime = new Date(this.rateLimitInfo.reset * 1000);
        const waitTime = resetTime.getTime() - Date.now();

        if (waitTime > 0) {
          console.log(`Waiting ${waitTime}ms for rate limit reset`);
          await new Promise((resolve) => setTimeout(resolve, waitTime));
        }
      }

      const request = this.requestQueue.shift();

      try {
        const response = await this.request(request.endpoint, request.options);
        request.resolve(response);
      } catch (error) {
        request.reject(error);
      }

      // Small delay between requests to avoid burst limits
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    this.processing = false;
  }
}
```

## Best Practices

### 1. Monitor Rate Limits

```javascript
// Set up rate limit monitoring
function monitorRateLimits(client) {
  setInterval(() => {
    const remaining = client.getRemainingRequests();
    const resetTime = client.getResetTime();

    console.log(`Rate Limit Status:
      Remaining: ${remaining}
      Resets at: ${resetTime.toISOString()}
    `);

    // Alert when approaching limit
    if (remaining < 10) {
      console.warn("⚠️  Approaching rate limit!");
    }
  }, 60000); // Check every minute
}
```

### 2. Implement Circuit Breaker

```javascript
class CircuitBreaker {
  constructor(threshold = 5, timeout = 60000) {
    this.threshold = threshold;
    this.timeout = timeout;
    this.failureCount = 0;
    this.state = "CLOSED"; // CLOSED, OPEN, HALF_OPEN
    this.nextAttempt = Date.now();
  }

  async call(fn) {
    if (this.state === "OPEN") {
      if (Date.now() < this.nextAttempt) {
        throw new Error("Circuit breaker is OPEN");
      }
      this.state = "HALF_OPEN";
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = "CLOSED";
  }

  onFailure() {
    this.failureCount++;
    if (this.failureCount >= this.threshold) {
      this.state = "OPEN";
      this.nextAttempt = Date.now() + this.timeout;
    }
  }
}

// Usage
const circuitBreaker = new CircuitBreaker();

async function makeAPICall() {
  return circuitBreaker.call(() => client.request("/v1/plan/generate"));
}
```

### 3. Batch Requests

```javascript
class BatchRequestManager {
  constructor(client, batchSize = 10, delay = 1000) {
    this.client = client;
    this.batchSize = batchSize;
    this.delay = delay;
    this.queue = [];
  }

  async add(request) {
    this.queue.push(request);

    if (this.queue.length >= this.batchSize) {
      await this.processBatch();
    }
  }

  async processBatch() {
    const batch = this.queue.splice(0, this.batchSize);

    // Process requests with delay between each
    for (const request of batch) {
      try {
        const response = await this.client.request(
          request.endpoint,
          request.options
        );
        request.resolve(response);
      } catch (error) {
        request.reject(error);
      }

      if (batch.indexOf(request) < batch.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, this.delay));
      }
    }
  }
}
```

### 4. Cache Responses

```javascript
class CachedClient extends RateLimitedClient {
  constructor(baseURL, token, cacheTTL = 300000) {
    // 5 minutes default
    super(baseURL, token);
    this.cache = new Map();
    this.cacheTTL = cacheTTL;
  }

  getCacheKey(endpoint, options) {
    return `${endpoint}_${JSON.stringify(options)}`;
  }

  async request(endpoint, options = {}) {
    const cacheKey = this.getCacheKey(endpoint, options);
    const cached = this.cache.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      console.log("Cache hit for", endpoint);
      return cached.response;
    }

    const response = await super.request(endpoint, options);

    // Only cache successful GET requests
    if ((!options.method || options.method === "GET") && response.ok) {
      this.cache.set(cacheKey, {
        response: response.clone(),
        timestamp: Date.now(),
      });
    }

    return response;
  }
}
```

## Testing Rate Limits

### Unit Tests

```javascript
describe("Rate Limiting", () => {
  test("should handle 429 responses gracefully", async () => {
    const mockFetch = jest
      .fn()
      .mockResolvedValueOnce({
        status: 429,
        headers: new Map([["Retry-After", "60"]]),
      })
      .mockResolvedValueOnce({
        status: 200,
        json: () => Promise.resolve({ success: true }),
      });

    global.fetch = mockFetch;

    const client = new RateLimitedClient("https://api.test.com", "token");
    const response = await client.request("/test");

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(response.status).toBe(200);
  });

  test("should respect rate limit headers", async () => {
    const client = new RateLimitedClient("https://api.test.com", "token");

    // Mock response with rate limit headers
    global.fetch = jest.fn().mockResolvedValue({
      status: 200,
      headers: new Map([
        ["X-RateLimit-Limit", "100"],
        ["X-RateLimit-Remaining", "50"],
        ["X-RateLimit-Reset", "1697207400"],
      ]),
    });

    await client.request("/test");

    expect(client.getRemainingRequests()).toBe(50);
    expect(client.getResetTime()).toEqual(new Date(1697207400 * 1000));
  });
});
```

### Load Testing

```bash
# Test rate limits with Apache Bench
ab -n 200 -c 10 -H "Authorization: Bearer <token>" \
   https://api.ai-nutritionist.com/v1/plan/generate

# Expected: Some requests should return 429 status
```

### Rate Limit Testing Script

```javascript
// test-rate-limits.js
async function testRateLimit(endpoint, limit) {
  const client = new RateLimitedClient(
    "https://api.ai-nutritionist.com/v1",
    process.env.API_TOKEN
  );

  let successCount = 0;
  let rateLimitCount = 0;

  for (let i = 0; i < limit + 10; i++) {
    try {
      const response = await client.request(endpoint);
      if (response.ok) {
        successCount++;
      }
    } catch (error) {
      if (error instanceof RateLimitError) {
        rateLimitCount++;
      }
    }
  }

  console.log(`Results for ${endpoint}:
    Successful requests: ${successCount}
    Rate limited requests: ${rateLimitCount}
    Expected limit: ${limit}
  `);
}

// Run tests
testRateLimit("/plan/generate", 3); // Free tier limit
testRateLimit("/analytics/events", 100); // Hourly limit
```

## Monitoring and Alerting

### Rate Limit Metrics

Track these metrics in your monitoring system:

```javascript
// Metrics to track
const metrics = {
  "api.rate_limit.requests_total": "Counter",
  "api.rate_limit.requests_rejected": "Counter",
  "api.rate_limit.remaining_quota": "Gauge",
  "api.rate_limit.reset_time": "Gauge",
  "api.rate_limit.retry_attempts": "Counter",
};

// Example with Prometheus client
const promClient = require("prom-client");

const rateLimitCounter = new promClient.Counter({
  name: "api_rate_limit_requests_total",
  help: "Total API requests by status",
  labelNames: ["endpoint", "status", "user_tier"],
});

const rateLimitGauge = new promClient.Gauge({
  name: "api_rate_limit_remaining",
  help: "Remaining rate limit quota",
  labelNames: ["endpoint", "user_id"],
});
```

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: rate_limiting
    rules:
      - alert: HighRateLimitUsage
        expr: |
          (api_rate_limit_requests_total{status="429"} / 
           api_rate_limit_requests_total) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rate limit rejection rate"
          description: "{{ $labels.endpoint }} has >10% rate limit rejections"

      - alert: RateLimitQuotaExhausted
        expr: api_rate_limit_remaining < 10
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Rate limit quota nearly exhausted"
          description: "User {{ $labels.user_id }} has <10 requests remaining"
```

## Troubleshooting

### Common Issues

**Q: Why am I getting 429 errors with a premium account?**
A: Check the specific endpoint limits. Some endpoints have separate limits regardless of tier.

**Q: Rate limit headers show remaining requests, but I'm still getting 429s**
A: You might be hitting burst limits. Reduce request frequency.

**Q: How do I increase my rate limits?**
A: Upgrade your subscription tier or contact support for custom limits.

**Q: Why do rate limits reset at different times?**
A: Different endpoints may have different reset intervals (hourly, daily, etc.).

### Debug Tools

```bash
# Check current rate limit status
curl -H "Authorization: Bearer <token>" \
     -I https://api.ai-nutritionist.com/v1/infrastructure/rate-limit/status/user_123

# Monitor rate limit headers
curl -H "Authorization: Bearer <token>" \
     -v https://api.ai-nutritionist.com/v1/plan/generate 2>&1 | grep -i "x-ratelimit"
```

### Support

For rate limit issues:

1. **Check documentation**: Verify endpoint-specific limits
2. **Monitor headers**: Use rate limit headers to track usage
3. **Implement retry logic**: Handle 429 responses gracefully
4. **Contact support**: For custom rate limit requirements

**Support Contact**: api-support@ai-nutritionist.com
