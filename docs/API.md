# API Documentation

## Overview

The AI Nutritionist Assistant provides RESTful APIs for WhatsApp/SMS integration, AI meal planning, user management, and multi-goal nutrition optimization. All APIs are deployed as AWS Lambda functions behind API Gateway.

## Base URL
```
https://your-api-gateway-url/
```

## Authentication

API endpoints use AWS IAM or API Gateway keys for authentication. For webhook endpoints, Twilio signature validation is implemented.

## Endpoints

### Multi-Goal Management

#### Add User Goal
**POST** `/user/{user_id}/goals`

Add a nutrition goal for the user. Supports both standard goals (budget, muscle_gain, weight_loss, etc.) and custom goals.

**Request Body:**
```json
{
  "goal_input": "budget friendly meals",
  "priority": 3
}
```

**Response:**
```json
{
  "success": true,
  "goal": {
    "goal_type": "budget",
    "priority": 3,
    "constraints": {
      "max_cost_per_meal": 4.00,
      "emphasized_foods": ["beans", "lentils", "rice"]
    },
    "created_at": "2025-09-11T10:00:00Z"
  },
  "acknowledgment": "Got it! I'll focus on budget-friendly in your meal plans.",
  "total_goals": 1
}
```

#### Handle Unknown/Custom Goal
**POST** `/user/{user_id}/goals/custom`

Process unknown or custom nutrition goals with intelligent dietary proxy mapping.

**Request Body:**
```json
{
  "goal_text": "skin health"
}
```

**Response:**
```json
{
  "success": true,
  "goal": {
    "goal_type": "custom",
    "label": "skin health",
    "priority": 2,
    "constraints": {
      "emphasized_foods": ["omega3_foods", "antioxidant_rich"],
      "required_nutrients": ["vitamin_c", "vitamin_e", "omega3"],
      "description": "Focus on omega-3s, antioxidants, and skin-supporting nutrients"
    }
  },
  "acknowledgment": "I don't have a dedicated skin health tracker, but I can focus on omega-3s, antioxidants, and skin-supporting nutrients.",
  "is_new_custom_goal": false
}
```

#### Update Goal Priorities
**PUT** `/user/{user_id}/goals/priorities`

Update priority rankings of user goals for constraint resolution.

**Request Body:**
```json
{
  "priority_updates": [
    {
      "goal_type": "budget",
      "priority": 4
    },
    {
      "goal_type": "muscle_gain", 
      "priority": 2
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Goal priorities updated successfully"
}
```

#### Get User Goals
**GET** `/user/{user_id}/goals`

Retrieve all user goals with priorities and constraints.

**Response:**
```json
{
  "goals": [
    {
      "goal_type": "budget",
      "priority": 4,
      "constraints": {...},
      "created_at": "2025-09-11T10:00:00Z"
    },
    {
      "goal_type": "custom",
      "label": "gut health",
      "priority": 2,
      "constraints": {...},
      "created_at": "2025-09-11T10:15:00Z"
    }
  ],
  "merged_constraints": {
    "max_cost_per_meal": 4.00,
    "protein_grams": 120,
    "emphasized_foods": ["beans", "lean_protein", "fermented_foods"],
    "quick_meal_preference": false
  },
  "ai_prompt_context": "User's nutrition goals (in priority order):\n1. Budget-Friendly (Critical priority)..."
}
```

#### Generate Multi-Goal Meal Plan
**POST** `/user/{user_id}/meal-plan/multi-goal`

Generate meal plan optimized for multiple user goals with constraint merging.

**Request Body:**
```json
{
  "days": 3,
  "preferences": {
    "exclude_recipes": ["recipe_id_1"],
    "preferred_meal_types": ["quick", "one_pot"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "meals": [
    {
      "meal_number": 1,
      "day": 1,
      "meal_type": "breakfast",
      "name": "Lentil & Egg Power Bowl",
      "recipe_id": "budget_protein_bowl",
      "cost_per_serving": 2.50,
      "prep_time": 15,
      "nutrition": {
        "calories": 380,
        "protein": 22,
        "fiber": 12,
        "sodium": 450
      },
      "goal_score": 0.85,
      "tags": ["budget", "protein", "quick"]
    }
  ],
  "constraints_met": {
    "cost": true,
    "protein": true,
    "prep_time": true
  },
  "trade_offs": [
    "Budget focus may limit premium protein sources, but I've maximized affordable high-protein options"
  ],
  "cost_breakdown": {
    "total_cost": 22.50,
    "avg_cost_per_meal": 2.50,
    "daily_cost": 7.50
  },
  "goal_satisfaction": {
    "budget": 0.9,
    "muscle_gain": 0.8,
    "custom_gut_health": 0.7
  },
  "message": "Multi-goal meal plan balancing budget-friendly, muscle building, and gut health!"
}
```

#### Get Trending Custom Goals
**GET** `/analytics/trending-custom-goals`

Get custom goals that are trending across users for potential promotion to standard goals.

**Query Parameters:**
- `min_users`: Minimum number of users (default: 5)

**Response:**
```json
{
  "trending_goals": [
    {
      "label": "skin health",
      "user_count": 12,
      "success_rate": 0.85,
      "common_constraints": {
        "emphasized_foods": ["omega3_foods", "antioxidant_rich"],
        "required_nutrients": ["vitamin_c", "vitamin_e"]
      }
    },
    {
      "label": "sleep optimization",
      "user_count": 8,
      "success_rate": 0.90,
      "common_constraints": {
        "emphasized_foods": ["magnesium_rich", "tryptophan_rich"],
        "avoided_foods": ["caffeine_evening"]
      }
    }
  ]
}
```

### Core Messaging

#### WhatsApp/SMS Webhook
**POST** `/webhook/whatsapp`

Processes incoming WhatsApp and SMS messages through the progressive personalization engine with multi-goal support.

**Request Body:**
```json
{
  "From": "+1234567890",
  "Body": "I want to eat on a budget, build muscle, and improve gut health",
  "MessageSid": "unique-message-id",
  "MediaUrl0": "https://api.twilio.com/photo.jpg",
  "MediaContentType0": "image/jpeg"
}
```

**Response:**
```json
{
  "statusCode": 200,
  "body": "Message processed successfully"
}
```

#### Multi-Goal Conversation Handler
**POST** `/conversation/multi-goal`

Process multi-goal conversations with intelligent goal parsing and prioritization.

**Request Body:**
```json
{
  "user_id": "user_123",
  "message": "budget is more important than muscle gain",
  "platform": "whatsapp"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Got it! I'll prioritize budget-friendly in your meal plans. 🎯\nWant me to update your meal plan with these new priorities? 🔄",
  "type": "prioritization_update",
  "next_action": "meal_plan_regeneration"
}
```

#### Payment Webhook
**POST** `/webhook/payment`

Handles Stripe payment callbacks for subscription management.

**Request Body:**
```json
{
  "type": "invoice.payment_succeeded",
  "data": {
    "object": {
      "customer": "cus_stripe_customer_id",
      "subscription": "sub_stripe_subscription_id",
      "amount_paid": 700
    }
  }
}
```

### Meal Management

#### Log Meal
**POST** `/meal/log`

Logs a meal with photo or text description for nutrition analysis.

**Request Body:**
```json
{
  "user_id": "user123",
  "meal_type": "lunch",
  "description": "Chicken Caesar salad",
  "photo_url": "https://s3.bucket/photo.jpg",
  "timestamp": "2025-09-11T14:30:00Z"
}
```

**Response:**
```json
{
  "meal_log": {
    "log_id": "log_456",
    "nutrition_analysis": {
      "calories": 450,
      "protein": 25,
      "carbs": 12,
      "fat": 35,
      "fiber": 4
    },
    "coaching_suggestions": [
      "Great protein choice! For dinner, try adding more fiber with vegetables.",
      "Your daily protein is on track. Consider a lighter dinner option."
    ],
    "auto_rebalancing": {
      "dinner_suggestions": ["grilled_salmon_vegetables", "quinoa_bowl"],
      "remaining_daily_budget": {
        "calories": 800,
        "protein": 15,
        "carbs": 100
      }
    }
  }
}
```

#### Generate Meal Plan
**POST** `/generate-meal-plan`

Creates personalized meal plans using progressive personalization data.

**Request Body:**
```json
{
  "user_id": "user123",
  "plan_type": "weekly",
  "preferences": {
    "dietary_restrictions": ["vegetarian"],
    "budget": 75,
    "cooking_time": 30,
    "household_size": 2
  },
  "personalization_context": {
    "previous_ratings": [4, 5, 3, 4],
    "preferred_cuisines": ["mediterranean", "asian"],
    "time_constraints": ["busy_weekdays"]
  }
}
```

**Response:**
```json
{
  "meal_plan": {
    "plan_id": "plan_789",
    "week_of": "2025-09-15",
    "total_budget": 68.50,
    "meals": [
      {
        "day": "Monday",
        "breakfast": {
          "name": "Mediterranean Quinoa Bowl",
          "prep_time": 15,
          "calories": 350,
          "cost": 3.25,
          "ingredients": ["quinoa", "tomatoes", "feta", "olives"]
        },
        "lunch": {
          "name": "Asian Lettuce Wraps",
          "prep_time": 20,
          "calories": 280,
          "cost": 4.50
        },
        "dinner": {
          "name": "Lentil Curry with Rice",
          "prep_time": 25,
          "calories": 420,
          "cost": 3.75
        }
      }
    ],
    "grocery_list": {
      "total_cost": 68.50,
      "affiliate_links": {
        "amazon_fresh": "https://amazon.com/cart/add?items=...",
        "instacart": "https://instacart.com/cart/...",
        "estimated_savings": 5.20
      },
      "items": [
        {"item": "Quinoa (2lb)", "cost": 8.99, "aisle": "grains"},
        {"item": "Cherry tomatoes", "cost": 3.49, "aisle": "produce"}
      ]
    },
    "personalization_notes": [
      "Reduced spice level based on previous feedback",
      "Added extra Mediterranean options (your favorite cuisine)",
      "All meals under 30 minutes as requested"
    ]
  }
}
```

### User Analytics

#### Get User Stats
**GET** `/user/{user_id}/stats`

Retrieves comprehensive nutrition and usage analytics.

**Query Parameters:**
- `period`: `daily`, `weekly`, `monthly`
- `include_trends`: `true`, `false`

**Response:**
```json
{
  "user_stats": {
    "current_period": "2025-09-01_2025-09-07",
    "nutrition_summary": {
      "average_daily_calories": 1650,
      "protein_percentage": 22,
      "carb_percentage": 45,
      "fat_percentage": 33,
      "fiber_grams": 28,
      "goal_adherence": 0.85
    },
    "meal_logging": {
      "meals_logged": 18,
      "photos_analyzed": 12,
      "manual_entries": 6,
      "average_rating": 4.2
    },
    "personalization_progress": {
      "preferences_learned": 15,
      "behavioral_patterns": 8,
      "accuracy_improvement": 0.23,
      "stage": "advanced_personalization"
    },
    "cost_analysis": {
      "average_weekly_grocery": 72.30,
      "affiliate_savings": 6.80,
      "budget_adherence": 0.96
    },
    "trends": {
      "weight_trend": "stable",
      "energy_level_trend": "improving",
      "satisfaction_trend": "increasing"
    }
  }
}
```

### Calendar Integration

#### Initialize Calendar Sync
**POST** `/calendar/sync`

Initiates Google Calendar OAuth flow for meal planning integration.

**Request Body:**
```json
{
  "user_id": "user123",
  "calendar_preferences": {
    "meal_prep_day": "sunday",
    "prep_time": "10:00",
    "grocery_day": "saturday",
    "cooking_reminders": true
  }
}
```

**Response:**
```json
{
  "oauth_url": "https://accounts.google.com/oauth/v2/auth?client_id=...",
  "state": "calendar_sync_state_token",
  "calendar_config": {
    "event_types": ["meal_prep", "grocery_shopping", "cooking_reminders"],
    "reminder_settings": {
      "prep_reminder": "1_day_before",
      "cooking_reminder": "30_minutes_before"
    }
  }
}
```

#### Calendar OAuth Callback
**POST** `/calendar/oauth/callback`

Handles Google Calendar OAuth callback and creates initial calendar events.

**Request Body:**
```json
{
  "code": "oauth_authorization_code",
  "state": "calendar_sync_state_token",
  "user_id": "user123"
}
```

### Household Management

#### Send Household Invite
**POST** `/household/invite`

Initiates GDPR-compliant household linking with double opt-in process.

**Request Body:**
```json
{
  "inviter_user_id": "user123",
  "invitee_phone": "+1234567891",
  "sharing_preferences": {
    "share_meal_plans": true,
    "share_grocery_lists": true,
    "share_nutrition_data": false,
    "share_conversation_history": false
  }
}
```

**Response:**
```json
{
  "invitation": {
    "invitation_id": "inv_456",
    "verification_code": "123456",
    "expires_at": "2025-09-14T12:00:00Z",
    "privacy_notice": "Invitee will receive privacy notice with consent options",
    "status": "sent"
  }
}
```

#### Accept Household Invite
**POST** `/household/accept`

Processes household invitation acceptance with explicit consent.

**Request Body:**
```json
{
  "verification_code": "123456",
  "invitee_phone": "+1234567891",
  "consent_given": {
    "data_sharing": true,
    "meal_plan_sharing": true,
    "grocery_list_sharing": true,
    "analytics_sharing": false
  }
}
```

### Usage & Billing

#### Get Usage Stats
**GET** `/user/{user_id}/usage`

Returns current subscription usage and tier entitlements.

**Response:**
```json
{
  "usage_summary": {
    "current_tier": "standard",
    "billing_period": "2025-09-01_2025-09-30",
    "usage": {
      "meal_plans_generated": 12,
      "photos_analyzed": 45,
      "ai_conversations": 78,
      "calendar_syncs": 1
    },
    "limits": {
      "meal_plans_generated": "unlimited",
      "photos_analyzed": "unlimited",
      "ai_conversations": "unlimited",
      "calendar_syncs": "unlimited"
    },
    "cost_tracking": {
      "ai_tokens_used": 15420,
      "estimated_cost": 2.35,
      "cost_per_interaction": 0.03
    },
    "upgrade_suggestions": {
      "suggested_tier": "premium",
      "reason": "heavy_photo_analysis_usage",
      "estimated_savings": 8.50
    }
  }
}
```

#### Update Subscription
**POST** `/user/{user_id}/subscription`

Updates user subscription tier with Stripe integration.

**Request Body:**
```json
{
  "new_tier": "premium",
  "payment_method": "pm_stripe_payment_method_id",
  "upgrade_reason": "family_features"
}
```

## Edamam API Integration

The application integrates with multiple Edamam APIs:

### Recipe Search API
- **Cost**: $0.002/call
- **Usage**: Finding recipes based on ingredients
- **Caching**: 24-hour cache to optimize costs

### Nutrition Analysis API  
- **Cost**: $0.005/call
- **Usage**: Analyzing nutritional content
- **Optimization**: Batch processing to reduce calls

### Food Database API
- **Cost**: $0.001/call  
- **Usage**: Ingredient identification and nutrition facts

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid authentication)
- `429` - Rate Limited
- `500` - Internal Server Error

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_PREFERENCES",
    "message": "Dietary preferences must be an array",
    "details": {}
  }
}
```

## Rate Limiting

- **WhatsApp/SMS**: 100 messages/minute per user
- **API calls**: 1000 requests/hour per API key
- **AI Generation**: 10 meal plans/hour per user (free tier)

## Cost Optimization Features

### Intelligent Caching
- Recipe data cached for 24 hours
- Nutrition analysis cached for 7 days
- User preferences cached in memory

### Batch Processing
- Multiple nutrition analyses in single API call
- Bulk recipe searches when possible

### Usage Analytics
- Real-time cost tracking
- Usage limits enforcement
- Cost alerts at 80% of budget

## Webhooks

### Twilio Webhook Validation
All Twilio webhooks are validated using signature verification:

```python
from twilio.request_validator import RequestValidator

def validate_twilio_signature(request):
    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)
```

### Retry Logic
- Automatic retry on transient failures
- Exponential backoff (1s, 2s, 4s, 8s)
- Dead letter queue for persistent failures

## Monitoring & Observability

### CloudWatch Metrics
- API response times
- Error rates by endpoint
- Cost per API call
- User engagement metrics

### Logging
- Structured JSON logging
- Request/response correlation IDs
- Performance metrics

### Alerts
- Error rate > 5%
- Response time > 2 seconds
- Daily cost > budget threshold

## International Support

### Phone Number Handling
- E.164 format validation
- Country code detection
- Timezone-aware scheduling

### Multi-language Support
- Spanish nutrition advice
- French meal planning
- Automatic language detection

## Security

### Data Protection
- Encryption at rest (DynamoDB)
- Encryption in transit (TLS 1.3)
- Input validation and sanitization

### Privacy Compliance
- GDPR compliant data handling
- User data export/deletion
- Consent management

### Rate Limiting & DDoS Protection
- AWS WAF integration
- IP-based rate limiting
- CAPTCHA for suspicious traffic

## Testing

### Local Development
```bash
# Start local API Gateway
sam local start-api

# Test webhook endpoint
curl -X POST http://localhost:3000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"From": "+1234567890", "Body": "test message"}'
```

### Integration Tests
```bash
# Run API tests
python -m pytest tests/test_api_integration.py -v

# Test with real Edamam API
python -m pytest tests/test_edamam_integration.py -v
```

## SDK Examples

### Python
```python
import requests

# Generate meal plan
response = requests.post(
    "https://api.ai-nutritionist.com/generate-meal-plan",
    json={
        "user_id": "user123",
        "dietary_preferences": ["gluten-free"],
        "budget": 100
    },
    headers={"Authorization": "Bearer your-api-key"}
)

meal_plan = response.json()
```

### JavaScript
```javascript
const response = await fetch('/generate-meal-plan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-api-key'
  },
  body: JSON.stringify({
    user_id: 'user123',
    dietary_preferences: ['vegan'],
    budget: 80
  })
});

const mealPlan = await response.json();
```
