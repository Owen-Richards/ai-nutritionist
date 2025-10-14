# AI Nutritionist API Documentation

## Overview

The AI Nutritionist API provides comprehensive access to meal planning, community features, gamification, analytics, and integration capabilities. This documentation covers all available endpoints, authentication methods, and best practices.

## Quick Start

### Authentication

All API requests require authentication using JWT tokens:

```bash
curl -H "Authorization: Bearer <your_jwt_token>" \
     https://api.ai-nutritionist.com/v1/plan/generate
```

### Get Started in 3 Steps

1. **Authenticate**: Obtain a JWT token
2. **Generate Plan**: Create your first meal plan
3. **Submit Feedback**: Improve recommendations

## API Reference

### Base URLs

- **Production**: `https://api.ai-nutritionist.com/v1`
- **Staging**: `https://staging-api.ai-nutritionist.com/v1`
- **Development**: `https://dev-api.ai-nutritionist.com/v1`

### Rate Limits

| Tier       | Requests/Hour | Burst Limit |
| ---------- | ------------- | ----------- |
| Free       | 100           | 10          |
| Premium    | 1,000         | 50          |
| Enterprise | 10,000        | 200         |

### Response Format

All responses follow a consistent JSON structure:

```json
{
  "data": {
    /* response data */
  },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total_count": 100
  },
  "links": {
    "self": "/v1/resource?page=1",
    "next": "/v1/resource?page=2",
    "prev": null
  }
}
```

### Error Handling

Errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.ai-nutritionist.com/problems/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The request body contains invalid data",
  "instance": "/v1/plan/generate",
  "errors": [
    {
      "field": "user_id",
      "message": "Field is required"
    }
  ]
}
```

## Core Services

### 🍽️ Meal Planning

Generate personalized meal plans based on dietary preferences, budget, and health goals.

**Key Endpoints:**

- `POST /v1/plan/generate` - Generate new meal plan
- `GET /v1/plan/{plan_id}` - Retrieve meal plan
- `POST /v1/plan/{plan_id}/feedback` - Submit meal feedback

### 👥 Community

Connect with other users through crews, reflections, and social features.

**Key Endpoints:**

- `POST /v1/community/crews/join` - Join a crew
- `POST /v1/community/reflections` - Share reflection
- `GET /v1/community/pulse` - Get community metrics

### 🎮 Gamification

Track progress with achievements, streaks, and challenges.

**Key Endpoints:**

- `GET /v1/gamification/summary` - Get progress summary
- `POST /v1/gamification/progress` - Update progress
- `GET /v1/gamification/achievements` - List achievements

### 📊 Analytics

Track usage patterns and generate insights.

**Key Endpoints:**

- `GET /v1/analytics/dashboard` - Get dashboard data
- `POST /v1/analytics/events` - Track events
- `GET /v1/analytics/insights` - Get user insights

### 🔧 Infrastructure

Monitor system health and manage configurations.

**Key Endpoints:**

- `GET /v1/infrastructure/health` - System health check
- `GET /v1/infrastructure/rate-limit/status/{id}` - Rate limit status
- `POST /v1/infrastructure/alerts` - Create alert

### 🔗 Integrations

Connect with calendar, grocery, and fitness platforms.

**Key Endpoints:**

- `POST /v1/integrations/calendar/auth` - Calendar OAuth
- `POST /v1/integrations/calendar/events` - Create events
- `POST /v1/integrations/fitness/sync` - Sync fitness data

## Event-Driven Architecture

The AI Nutritionist platform uses WebSocket connections for real-time events:

```javascript
const ws = new WebSocket("wss://events.ai-nutritionist.com");

ws.on("message", (data) => {
  const event = JSON.parse(data);

  switch (event.event_type) {
    case "plan.generated":
      handlePlanGenerated(event.data);
      break;
    case "achievement.unlocked":
      showAchievement(event.data);
      break;
  }
});
```

### Event Categories

- **User Events**: Registration, profile updates
- **Meal Planning**: Plan generation, feedback
- **Community**: Crew activities, reflections
- **Gamification**: Progress, achievements
- **Analytics**: Usage tracking
- **Infrastructure**: Health, alerts
- **Integrations**: Calendar, fitness sync
- **Billing**: Subscriptions, payments

## Webhooks

Configure webhooks to receive real-time notifications:

### Supported Events

| Event                  | Description            |
| ---------------------- | ---------------------- |
| `plan.generated`       | Meal plan generated    |
| `feedback.submitted`   | User feedback received |
| `subscription.updated` | Subscription changed   |
| `achievement.unlocked` | New achievement        |

### Webhook Configuration

```json
{
  "url": "https://your-app.com/webhooks/ai-nutritionist",
  "events": ["plan.generated", "feedback.submitted"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload

```json
{
  "id": "webhook_123e4567-e89b-12d3-a456-426614174000",
  "event_type": "plan.generated",
  "timestamp": "2024-10-13T15:30:00Z",
  "data": {
    "plan_id": "plan_abc123",
    "user_id": "user_123456",
    "meals": [...],
    "estimated_cost": 89.45
  },
  "api_version": "2.0.0"
}
```

## SDKs and Libraries

### Official SDKs

- **JavaScript/TypeScript**: `npm install @ai-nutritionist/api-client`
- **Python**: `pip install ai-nutritionist-api`
- **React Native**: `npm install @ai-nutritionist/react-native`

### Community SDKs

- **PHP**: [ai-nutritionist-php](https://github.com/community/ai-nutritionist-php)
- **Ruby**: [ai-nutritionist-ruby](https://github.com/community/ai-nutritionist-ruby)
- **Go**: [ai-nutritionist-go](https://github.com/community/ai-nutritionist-go)

## Best Practices

### Performance

1. **Caching**: Use ETags for conditional requests
2. **Pagination**: Implement proper pagination for large datasets
3. **Compression**: Enable gzip compression
4. **Connection Pooling**: Reuse HTTP connections

### Security

1. **Authentication**: Always use HTTPS and valid JWT tokens
2. **Input Validation**: Validate all input parameters
3. **Rate Limiting**: Respect rate limits and implement backoff
4. **Webhook Verification**: Verify webhook signatures

### Error Handling

1. **Retry Logic**: Implement exponential backoff for retries
2. **Graceful Degradation**: Handle API failures gracefully
3. **Logging**: Log all API interactions for debugging
4. **Monitoring**: Monitor API response times and error rates

## Support

### Getting Help

- **Documentation**: [docs.ai-nutritionist.com](https://docs.ai-nutritionist.com)
- **Support Email**: api-support@ai-nutritionist.com
- **Community Forum**: [community.ai-nutritionist.com](https://community.ai-nutritionist.com)
- **GitHub Issues**: [github.com/ai-nutritionist/api-issues](https://github.com/ai-nutritionist/api-issues)

### Status Page

Monitor API status and uptime: [status.ai-nutritionist.com](https://status.ai-nutritionist.com)

### Changelog

Stay updated with API changes: [changelog.ai-nutritionist.com](https://changelog.ai-nutritionist.com)
