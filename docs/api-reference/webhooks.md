# Webhook Guide

## Overview

Webhooks allow your application to receive real-time notifications when events occur in the AI Nutritionist platform. Instead of polling the API for changes, webhooks deliver event data directly to your configured endpoint.

## Webhook Events

### Available Events

| Event Type                 | Description                    | Frequency         |
| -------------------------- | ------------------------------ | ----------------- |
| `plan.generated`           | Meal plan generation completed | Per plan          |
| `plan.failed`              | Meal plan generation failed    | Per failure       |
| `feedback.submitted`       | User submitted meal feedback   | Per feedback      |
| `user.registered`          | New user registered            | Per registration  |
| `user.profile_updated`     | User profile modified          | Per update        |
| `crew.joined`              | User joined a crew             | Per join          |
| `reflection.shared`        | User shared reflection         | Per reflection    |
| `achievement.unlocked`     | User unlocked achievement      | Per achievement   |
| `challenge.completed`      | User completed challenge       | Per completion    |
| `subscription.created`     | Subscription created           | Per subscription  |
| `subscription.updated`     | Subscription status changed    | Per change        |
| `subscription.cancelled`   | Subscription cancelled         | Per cancellation  |
| `payment.succeeded`        | Payment processed successfully | Per payment       |
| `payment.failed`           | Payment processing failed      | Per failure       |
| `integration.connected`    | External service connected     | Per connection    |
| `integration.disconnected` | External service disconnected  | Per disconnection |

### Event Categories

**User Events**

- User lifecycle and profile changes
- Authentication and security events

**Meal Planning Events**

- Plan generation and modifications
- Feedback and preferences

**Community Events**

- Social interactions and crew activities
- Reflections and shared content

**Gamification Events**

- Progress tracking and achievements
- Challenge completions and streaks

**Billing Events**

- Subscription and payment processing
- Invoice and billing updates

**Integration Events**

- Third-party service connections
- Data synchronization events

## Webhook Configuration

### Creating a Webhook

```bash
curl -X POST https://api.ai-nutritionist.com/v1/webhooks \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhooks/ai-nutritionist",
    "events": [
      "plan.generated",
      "feedback.submitted",
      "subscription.updated"
    ],
    "secret": "your_webhook_secret",
    "description": "Production webhook for meal planning events"
  }'
```

**Response:**

```json
{
  "id": "webhook_123e4567-e89b-12d3-a456-426614174000",
  "url": "https://your-app.com/webhooks/ai-nutritionist",
  "events": ["plan.generated", "feedback.submitted", "subscription.updated"],
  "secret": "your_webhook_secret",
  "status": "active",
  "created_at": "2024-10-13T15:30:00Z",
  "last_delivery": null,
  "delivery_count": 0,
  "failure_count": 0
}
```

### Listing Webhooks

```bash
curl -H "Authorization: Bearer <your_token>" \
     https://api.ai-nutritionist.com/v1/webhooks
```

### Updating a Webhook

```bash
curl -X PUT https://api.ai-nutritionist.com/v1/webhooks/webhook_123 \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "events": ["plan.generated", "plan.failed"],
    "status": "active"
  }'
```

### Deleting a Webhook

```bash
curl -X DELETE https://api.ai-nutritionist.com/v1/webhooks/webhook_123 \
  -H "Authorization: Bearer <your_token>"
```

## Webhook Payload Format

### Standard Payload Structure

```json
{
  "id": "event_123e4567-e89b-12d3-a456-426614174000",
  "event_type": "plan.generated",
  "timestamp": "2024-10-13T15:30:00Z",
  "api_version": "2.0.0",
  "data": {
    "plan_id": "plan_abc123",
    "user_id": "user_123456",
    "week_start": "2024-10-14",
    "estimated_cost": 89.45,
    "meal_count": 21,
    "generation_time_ms": 3250
  },
  "metadata": {
    "source": "api",
    "correlation_id": "corr_789xyz",
    "user_tier": "premium"
  }
}
```

### Event-Specific Payloads

#### Plan Generated Event

```json
{
  "id": "event_123e4567-e89b-12d3-a456-426614174000",
  "event_type": "plan.generated",
  "timestamp": "2024-10-13T15:30:00Z",
  "api_version": "2.0.0",
  "data": {
    "plan_id": "plan_abc123",
    "user_id": "user_123456",
    "week_start": "2024-10-14",
    "generated_at": "2024-10-13T15:30:00Z",
    "estimated_cost": 89.45,
    "total_calories": 8400,
    "meal_count": 21,
    "generation_time_ms": 3250,
    "preferences": {
      "dietary_restrictions": ["vegetarian"],
      "budget_per_week": 120.0,
      "servings": 4
    },
    "meals": [
      {
        "meal_id": "meal_789",
        "day": "monday",
        "meal_type": "dinner",
        "title": "Mediterranean Quinoa Bowl",
        "calories": 520,
        "prep_minutes": 30,
        "cost": 8.5
      }
    ],
    "grocery_list": [
      {
        "name": "Quinoa",
        "quantity": 2,
        "unit": "cups",
        "estimated_cost": 4.99
      }
    ]
  }
}
```

#### Feedback Submitted Event

```json
{
  "id": "event_456e7890-f12b-34c5-d678-901234567890",
  "event_type": "feedback.submitted",
  "timestamp": "2024-10-13T18:45:00Z",
  "api_version": "2.0.0",
  "data": {
    "feedback_id": "feedback_xyz789",
    "user_id": "user_123456",
    "plan_id": "plan_abc123",
    "meal_id": "meal_789",
    "rating": 4,
    "emoji": "😋",
    "comment": "Loved the flavors but could use more protein",
    "consumed_at": "2024-10-13T18:30:00Z",
    "sentiment": "positive",
    "feedback_type": "meal_rating"
  }
}
```

#### Subscription Updated Event

```json
{
  "id": "event_789f0123-4567-8901-2345-678901234567",
  "event_type": "subscription.updated",
  "timestamp": "2024-10-13T20:15:00Z",
  "api_version": "2.0.0",
  "data": {
    "user_id": "user_123456",
    "subscription_id": "sub_premium_123",
    "previous_tier": "free",
    "new_tier": "premium",
    "status": "active",
    "billing_cycle": "monthly",
    "amount": 29.99,
    "currency": "USD",
    "effective_date": "2024-10-13T20:15:00Z",
    "features_unlocked": [
      "unlimited_plans",
      "advanced_analytics",
      "priority_support"
    ]
  }
}
```

#### Achievement Unlocked Event

```json
{
  "id": "event_abc123def456",
  "event_type": "achievement.unlocked",
  "timestamp": "2024-10-13T16:20:00Z",
  "api_version": "2.0.0",
  "data": {
    "user_id": "user_123456",
    "achievement_id": "streak_master_7",
    "achievement_type": "streak",
    "title": "Week Warrior",
    "description": "Maintained a 7-day meal planning streak",
    "points_awarded": 100,
    "rarity": "uncommon",
    "category": "consistency",
    "milestone_reached": true,
    "streak_count": 7,
    "unlocked_at": "2024-10-13T16:20:00Z"
  }
}
```

## Webhook Security

### Signature Verification

Every webhook request includes a signature header for verification:

```http
POST /webhooks/ai-nutritionist HTTP/1.1
Host: your-app.com
Content-Type: application/json
X-AI-Nutritionist-Signature: sha256=a1b2c3d4e5f6...
X-AI-Nutritionist-Timestamp: 1697203800
X-AI-Nutritionist-Webhook-Id: webhook_123e4567
User-Agent: AI-Nutritionist-Webhooks/2.0
```

### Verifying Signatures

#### Node.js Example

```javascript
const crypto = require("crypto");
const express = require("express");
const app = express();

// Middleware to verify webhook signatures
function verifyWebhookSignature(req, res, next) {
  const signature = req.headers["x-ai-nutritionist-signature"];
  const timestamp = req.headers["x-ai-nutritionist-timestamp"];
  const webhookSecret = process.env.WEBHOOK_SECRET;

  if (!signature || !timestamp) {
    return res.status(401).json({ error: "Missing signature headers" });
  }

  // Check timestamp (reject requests older than 5 minutes)
  const currentTimestamp = Math.floor(Date.now() / 1000);
  if (Math.abs(currentTimestamp - parseInt(timestamp)) > 300) {
    return res.status(401).json({ error: "Request timestamp too old" });
  }

  // Create signature payload
  const payload = timestamp + "." + JSON.stringify(req.body);
  const expectedSignature = crypto
    .createHmac("sha256", webhookSecret)
    .update(payload)
    .digest("hex");

  const providedSignature = signature.replace("sha256=", "");

  // Use crypto.timingSafeEqual to prevent timing attacks
  const signatureBuffer = Buffer.from(providedSignature, "hex");
  const expectedBuffer = Buffer.from(expectedSignature, "hex");

  if (signatureBuffer.length !== expectedBuffer.length) {
    return res.status(401).json({ error: "Invalid signature" });
  }

  if (!crypto.timingSafeEqual(signatureBuffer, expectedBuffer)) {
    return res.status(401).json({ error: "Invalid signature" });
  }

  next();
}

// Webhook endpoint
app.post(
  "/webhooks/ai-nutritionist",
  express.raw({ type: "application/json" }),
  verifyWebhookSignature,
  (req, res) => {
    const event = JSON.parse(req.body);

    console.log("Received webhook:", event.event_type);

    // Process the event
    handleWebhookEvent(event);

    res.status(200).json({ received: true });
  }
);
```

#### Python Example

```python
import hashlib
import hmac
import time
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

def verify_webhook_signature(payload, signature, timestamp, secret):
    """Verify webhook signature"""

    # Check timestamp (reject requests older than 5 minutes)
    current_timestamp = int(time.time())
    if abs(current_timestamp - int(timestamp)) > 300:
        return False

    # Create signature payload
    signature_payload = f"{timestamp}.{payload}"
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        signature_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    provided_signature = signature.replace('sha256=', '')

    return hmac.compare_digest(expected_signature, provided_signature)

@app.route('/webhooks/ai-nutritionist', methods=['POST'])
def handle_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-AI-Nutritionist-Signature')
    timestamp = request.headers.get('X-AI-Nutritionist-Timestamp')

    if not verify_webhook_signature(payload, signature, timestamp, WEBHOOK_SECRET):
        return jsonify({'error': 'Invalid signature'}), 401

    event = json.loads(payload)

    # Process the event
    handle_webhook_event(event)

    return jsonify({'received': True})
```

#### PHP Example

```php
<?php
function verifyWebhookSignature($payload, $signature, $timestamp, $secret) {
    // Check timestamp
    $currentTimestamp = time();
    if (abs($currentTimestamp - intval($timestamp)) > 300) {
        return false;
    }

    // Create signature payload
    $signaturePayload = $timestamp . '.' . $payload;
    $expectedSignature = hash_hmac('sha256', $signaturePayload, $secret);
    $providedSignature = str_replace('sha256=', '', $signature);

    return hash_equals($expectedSignature, $providedSignature);
}

// Webhook handler
$payload = file_get_contents('php://input');
$signature = $_SERVER['HTTP_X_AI_NUTRITIONIST_SIGNATURE'] ?? '';
$timestamp = $_SERVER['HTTP_X_AI_NUTRITIONIST_TIMESTAMP'] ?? '';

if (!verifyWebhookSignature($payload, $signature, $timestamp, $webhookSecret)) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid signature']);
    exit;
}

$event = json_decode($payload, true);

// Process the event
handleWebhookEvent($event);

http_response_code(200);
echo json_encode(['received' => true]);
?>
```

## Event Handling

### Event Router Pattern

```javascript
class WebhookEventRouter {
  constructor() {
    this.handlers = new Map();
  }

  register(eventType, handler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType).push(handler);
  }

  async handle(event) {
    const handlers = this.handlers.get(event.event_type) || [];

    if (handlers.length === 0) {
      console.warn(`No handlers registered for event: ${event.event_type}`);
      return;
    }

    // Execute all handlers for this event type
    const results = await Promise.allSettled(
      handlers.map((handler) => handler(event))
    );

    // Log any handler failures
    results.forEach((result, index) => {
      if (result.status === "rejected") {
        console.error(
          `Handler ${index} failed for ${event.event_type}:`,
          result.reason
        );
      }
    });
  }
}

// Set up event handlers
const router = new WebhookEventRouter();

router.register("plan.generated", async (event) => {
  const { user_id, plan_id } = event.data;

  // Send notification to user
  await sendPushNotification(user_id, {
    title: "Your meal plan is ready!",
    body: "Check out your personalized weekly meal plan",
    deep_link: `app://plan/${plan_id}`,
  });

  // Update user stats
  await updateUserStats(user_id, {
    plans_generated: 1,
    last_plan_date: event.timestamp,
  });
});

router.register("feedback.submitted", async (event) => {
  const { user_id, rating, comment } = event.data;

  // Update recommendation engine
  await updateRecommendationModel(user_id, rating, comment);

  // Send thank you message for detailed feedback
  if (comment && comment.length > 50) {
    await sendEmail(user_id, "feedback_thank_you", {
      feedback: comment,
    });
  }
});

router.register("subscription.updated", async (event) => {
  const { user_id, new_tier, features_unlocked } = event.data;

  // Update user permissions
  await updateUserPermissions(user_id, new_tier);

  // Send welcome message for premium users
  if (new_tier === "premium") {
    await sendWelcomeToPremium(user_id, features_unlocked);
  }
});

// Main webhook handler
async function handleWebhookEvent(event) {
  try {
    // Log the event
    console.log(
      `Processing webhook: ${event.event_type} at ${event.timestamp}`
    );

    // Route to appropriate handlers
    await router.handle(event);

    // Store event for analytics
    await storeEvent(event);
  } catch (error) {
    console.error("Webhook processing failed:", error);
    throw error; // Re-throw to trigger retry
  }
}
```

### Event Processing Patterns

#### Immediate Processing

```javascript
// Process events immediately
router.register("achievement.unlocked", async (event) => {
  const { user_id, achievement_id, points_awarded } = event.data;

  // Update user's point balance immediately
  await updateUserPoints(user_id, points_awarded);

  // Send real-time notification
  await sendRealTimeNotification(user_id, {
    type: "achievement",
    data: event.data,
  });
});
```

#### Queued Processing

```javascript
// Queue events for background processing
router.register("plan.generated", async (event) => {
  // Add to processing queue
  await addToQueue("plan_processing", event, {
    delay: 0,
    attempts: 3,
    backoff: "exponential",
  });
});

// Background job processor
async function processPlanGenerated(job) {
  const event = job.data;
  const { user_id, plan_id } = event.data;

  // Heavy processing tasks
  await generateNutritionAnalysis(plan_id);
  await updatePersonalizationModel(user_id);
  await generateShoppingList(plan_id);
  await scheduleFollowUpReminders(user_id);
}
```

#### Batch Processing

```javascript
// Collect events for batch processing
class EventBatcher {
  constructor(batchSize = 100, flushInterval = 30000) {
    this.events = [];
    this.batchSize = batchSize;

    setInterval(() => this.flush(), flushInterval);
  }

  add(event) {
    this.events.push(event);

    if (this.events.length >= this.batchSize) {
      this.flush();
    }
  }

  async flush() {
    if (this.events.length === 0) return;

    const batch = this.events.splice(0);

    try {
      await this.processBatch(batch);
    } catch (error) {
      console.error("Batch processing failed:", error);
      // Re-queue failed events
      this.events.unshift(...batch);
    }
  }

  async processBatch(events) {
    // Group events by type
    const eventGroups = events.reduce((groups, event) => {
      const type = event.event_type;
      if (!groups[type]) groups[type] = [];
      groups[type].push(event);
      return groups;
    }, {});

    // Process each group
    await Promise.all(
      Object.entries(eventGroups).map(([type, events]) =>
        this.processBatchByType(type, events)
      )
    );
  }

  async processBatchByType(eventType, events) {
    switch (eventType) {
      case "feedback.submitted":
        await this.processFeedbackBatch(events);
        break;
      case "analytics.event":
        await this.processAnalyticsBatch(events);
        break;
      default:
        // Process individually
        await Promise.all(events.map((event) => router.handle(event)));
    }
  }
}

const batcher = new EventBatcher();

router.register("feedback.submitted", (event) => {
  batcher.add(event);
});
```

## Error Handling and Retries

### Webhook Delivery Retry Policy

The AI Nutritionist platform implements automatic retry for failed webhook deliveries:

| Attempt | Delay      | Total Time |
| ------- | ---------- | ---------- |
| 1       | Immediate  | 0s         |
| 2       | 1 minute   | 1m         |
| 3       | 5 minutes  | 6m         |
| 4       | 15 minutes | 21m        |
| 5       | 1 hour     | 1h 21m     |
| 6       | 4 hours    | 5h 21m     |
| 7       | 12 hours   | 17h 21m    |

### Handling Failed Deliveries

```javascript
// Webhook failure handler
app.post("/webhooks/ai-nutritionist", async (req, res) => {
  try {
    const event = JSON.parse(req.body);

    // Process the event
    await handleWebhookEvent(event);

    // Success response
    res.status(200).json({ received: true });
  } catch (error) {
    console.error("Webhook processing failed:", error);

    // Different responses based on error type
    if (error.code === "TEMPORARY_ERROR") {
      // Temporary error - retry
      res.status(500).json({
        error: "Temporary processing error",
        retry: true,
      });
    } else if (error.code === "PERMANENT_ERROR") {
      // Permanent error - don't retry
      res.status(400).json({
        error: "Permanent processing error",
        retry: false,
      });
    } else {
      // Unknown error - retry
      res.status(500).json({
        error: "Unknown processing error",
        retry: true,
      });
    }
  }
});
```

### Dead Letter Queue

```javascript
// Handle permanently failed webhooks
router.register("webhook.failed", async (event) => {
  const { webhook_id, event_data, failure_count, last_error } = event.data;

  if (failure_count >= 7) {
    // Send alert to ops team
    await sendAlert("webhook_failure", {
      webhook_id,
      event_type: event_data.event_type,
      failure_count,
      last_error,
    });

    // Store in dead letter queue for manual processing
    await storeInDeadLetterQueue(event_data);
  }
});
```

## Testing Webhooks

### Local Testing with ngrok

```bash
# Install ngrok
npm install -g ngrok

# Start your local webhook server
node webhook-server.js &

# Expose local server to internet
ngrok http 3000

# Use the ngrok URL for webhook configuration
curl -X POST https://api.ai-nutritionist.com/v1/webhooks \
  -H "Authorization: Bearer <token>" \
  -d '{
    "url": "https://abc123.ngrok.io/webhooks/ai-nutritionist",
    "events": ["plan.generated"]
  }'
```

### Webhook Testing Server

```javascript
// Simple webhook testing server
const express = require("express");
const app = express();

app.use(express.json());

app.post("/webhooks/ai-nutritionist", (req, res) => {
  console.log("Received webhook:");
  console.log("Headers:", req.headers);
  console.log("Body:", JSON.stringify(req.body, null, 2));

  res.status(200).json({ received: true });
});

app.listen(3000, () => {
  console.log("Webhook test server running on port 3000");
});
```

### Unit Tests

```javascript
const request = require("supertest");
const crypto = require("crypto");

describe("Webhook Handler", () => {
  const webhookSecret = "test_secret";

  function createSignature(payload, timestamp) {
    const signaturePayload = `${timestamp}.${payload}`;
    return (
      "sha256=" +
      crypto
        .createHmac("sha256", webhookSecret)
        .update(signaturePayload)
        .digest("hex")
    );
  }

  test("should process valid webhook", async () => {
    const payload = JSON.stringify({
      event_type: "plan.generated",
      data: { plan_id: "test_plan" },
    });
    const timestamp = Math.floor(Date.now() / 1000);
    const signature = createSignature(payload, timestamp);

    const response = await request(app)
      .post("/webhooks/ai-nutritionist")
      .set("X-AI-Nutritionist-Signature", signature)
      .set("X-AI-Nutritionist-Timestamp", timestamp.toString())
      .send(payload)
      .expect(200);

    expect(response.body.received).toBe(true);
  });

  test("should reject invalid signature", async () => {
    const payload = JSON.stringify({
      event_type: "plan.generated",
      data: { plan_id: "test_plan" },
    });
    const timestamp = Math.floor(Date.now() / 1000);

    await request(app)
      .post("/webhooks/ai-nutritionist")
      .set("X-AI-Nutritionist-Signature", "sha256=invalid")
      .set("X-AI-Nutritionist-Timestamp", timestamp.toString())
      .send(payload)
      .expect(401);
  });

  test("should reject old timestamp", async () => {
    const payload = JSON.stringify({
      event_type: "plan.generated",
      data: { plan_id: "test_plan" },
    });
    const oldTimestamp = Math.floor(Date.now() / 1000) - 400; // 400 seconds ago
    const signature = createSignature(payload, oldTimestamp);

    await request(app)
      .post("/webhooks/ai-nutritionist")
      .set("X-AI-Nutritionist-Signature", signature)
      .set("X-AI-Nutritionist-Timestamp", oldTimestamp.toString())
      .send(payload)
      .expect(401);
  });
});
```

## Webhook Monitoring

### Webhook Analytics

```javascript
// Track webhook metrics
class WebhookMetrics {
  constructor() {
    this.deliveryAttempts = 0;
    this.successfulDeliveries = 0;
    this.failedDeliveries = 0;
    this.averageResponseTime = 0;
  }

  recordDelivery(success, responseTime) {
    this.deliveryAttempts++;

    if (success) {
      this.successfulDeliveries++;
    } else {
      this.failedDeliveries++;
    }

    // Update average response time
    this.averageResponseTime =
      (this.averageResponseTime * (this.deliveryAttempts - 1) + responseTime) /
      this.deliveryAttempts;
  }

  getSuccessRate() {
    if (this.deliveryAttempts === 0) return 0;
    return this.successfulDeliveries / this.deliveryAttempts;
  }

  getMetrics() {
    return {
      delivery_attempts: this.deliveryAttempts,
      successful_deliveries: this.successfulDeliveries,
      failed_deliveries: this.failedDeliveries,
      success_rate: this.getSuccessRate(),
      average_response_time: this.averageResponseTime,
    };
  }
}
```

### Health Check Endpoint

```javascript
// Webhook health check
app.get("/webhooks/health", (req, res) => {
  const metrics = webhookMetrics.getMetrics();

  res.json({
    status: metrics.success_rate > 0.95 ? "healthy" : "degraded",
    metrics,
    last_delivery: lastDeliveryTime,
    webhook_count: activeWebhooks.length,
  });
});
```

## Best Practices

### 1. Idempotency

Ensure your webhook handlers are idempotent:

```javascript
// Use event ID to prevent duplicate processing
const processedEvents = new Set();

router.register("plan.generated", async (event) => {
  if (processedEvents.has(event.id)) {
    console.log(`Event ${event.id} already processed, skipping`);
    return;
  }

  try {
    await processPlanGenerated(event);
    processedEvents.add(event.id);
  } catch (error) {
    // Don't mark as processed if it failed
    throw error;
  }
});
```

### 2. Timeout Handling

Set appropriate timeouts for webhook processing:

```javascript
// Add timeout to webhook processing
async function handleWebhookWithTimeout(event, timeoutMs = 30000) {
  return Promise.race([
    handleWebhookEvent(event),
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error("Webhook timeout")), timeoutMs);
    }),
  ]);
}
```

### 3. Graceful Degradation

Handle webhook failures gracefully:

```javascript
router.register("plan.generated", async (event) => {
  try {
    // Primary processing
    await processPlanGenerated(event);
  } catch (error) {
    console.error("Primary processing failed:", error);

    try {
      // Fallback processing
      await processPlanGeneratedFallback(event);
    } catch (fallbackError) {
      console.error("Fallback processing failed:", fallbackError);

      // Queue for manual processing
      await queueForManualProcessing(event);
    }
  }
});
```

### 4. Rate Limiting

Implement rate limiting for webhook endpoints:

```javascript
const rateLimit = require("express-rate-limit");

const webhookLimiter = rateLimit({
  windowMs: 1000, // 1 second
  max: 100, // Limit each IP to 100 requests per windowMs
  message: "Too many webhook requests",
  standardHeaders: true,
  legacyHeaders: false,
});

app.use("/webhooks", webhookLimiter);
```

## Troubleshooting

### Common Issues

**Q: My webhook endpoint isn't receiving events**
A: Check webhook configuration, URL accessibility, and firewall rules.

**Q: Getting signature verification errors**
A: Verify webhook secret, check timestamp handling, and ensure payload isn't modified.

**Q: Webhooks are being retried repeatedly**
A: Check your endpoint's response codes and processing logic.

**Q: Missing some webhook events**
A: Check event filtering configuration and endpoint availability during delivery.

### Debug Tools

```bash
# Test webhook endpoint
curl -X POST https://your-app.com/webhooks/ai-nutritionist \
  -H "Content-Type: application/json" \
  -H "X-AI-Nutritionist-Signature: sha256=test" \
  -H "X-AI-Nutritionist-Timestamp: $(date +%s)" \
  -d '{"event_type":"test","data":{}}'

# Check webhook delivery logs
curl -H "Authorization: Bearer <token>" \
     https://api.ai-nutritionist.com/v1/webhooks/webhook_123/deliveries
```

### Support

For webhook issues:

1. **Check logs**: Review webhook delivery logs in the dashboard
2. **Test locally**: Use ngrok for local testing
3. **Verify signatures**: Ensure proper signature verification
4. **Monitor health**: Set up webhook health monitoring
5. **Contact support**: For persistent delivery issues

**Support Contact**: webhook-support@ai-nutritionist.com
