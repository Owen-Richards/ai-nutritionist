# cURL Examples

This guide provides comprehensive cURL examples for all AI Nutritionist API endpoints.

## Table of Contents

- [Authentication](#authentication)
- [Meal Planning](#meal-planning)
- [Community Features](#community-features)
- [Gamification](#gamification)
- [Analytics](#analytics)
- [Integrations](#integrations)
- [Infrastructure](#infrastructure)
- [Error Handling](#error-handling)
- [Bash Scripts](#bash-scripts)

## Environment Setup

Set up environment variables for easier testing:

```bash
# Set base configuration
export API_BASE_URL="https://api.ai-nutritionist.com/v1"
export API_TOKEN="your_api_token_here"
export USER_ID="user_123456"

# Content type header (used in most requests)
export CONTENT_TYPE="Content-Type: application/json"
export AUTH_HEADER="Authorization: Bearer $API_TOKEN"
```

## Authentication

### Initiate Authentication

```bash
# Start SMS authentication
curl -X POST "$API_BASE_URL/auth/login" \
  -H "$CONTENT_TYPE" \
  -d '{
    "channel": "sms",
    "identifier": "+1234567890"
  }'

# Response:
# {
#   "success": true,
#   "message": "Verification code sent",
#   "expires_in": 300,
#   "rate_limit": {
#     "remaining": 4,
#     "reset_time": "2024-10-13T15:35:00Z"
#   }
# }
```

```bash
# Start email authentication
curl -X POST "$API_BASE_URL/auth/login" \
  -H "$CONTENT_TYPE" \
  -d '{
    "channel": "email",
    "identifier": "user@example.com"
  }'
```

### Verify Authentication Code

```bash
# Verify the received code
curl -X POST "$API_BASE_URL/auth/verify" \
  -H "$CONTENT_TYPE" \
  -d '{
    "identifier": "+1234567890",
    "code": "123456"
  }'

# Response:
# {
#   "success": true,
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "expires_in": 3600,
#   "user": {
#     "user_id": "user_123456",
#     "phone_number": "+1234567890",
#     "created_at": "2024-01-15T10:30:00Z",
#     "preferences": {
#       "dietary_restrictions": [],
#       "notification_preferences": {
#         "meal_reminders": true,
#         "community_updates": true
#       }
#     }
#   }
# }
```

### Refresh Token

```bash
# Refresh expired access token
curl -X POST "$API_BASE_URL/auth/refresh" \
  -H "$CONTENT_TYPE" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'

# Update your environment variable with the new token
export API_TOKEN="new_access_token_here"
export AUTH_HEADER="Authorization: Bearer $API_TOKEN"
```

## Meal Planning

### Generate Meal Plan

```bash
# Generate a basic meal plan
curl -X POST "$API_BASE_URL/plan/generate" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "preferences": {
      "dietary_restrictions": ["vegetarian", "gluten_free"],
      "cuisine_preferences": ["mediterranean", "asian"],
      "budget_per_week": 120.00,
      "servings": 4,
      "prep_time_preference": "moderate",
      "equipment_available": ["oven", "stovetop", "blender"]
    },
    "week_start": "2024-10-14",
    "force_new": false
  }'
```

```bash
# Generate plan with minimal preferences
curl -X POST "$API_BASE_URL/plan/generate" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "preferences": {
      "budget_per_week": 80.00,
      "servings": 2
    }
  }'
```

### Retrieve Existing Plan

```bash
# Get a specific meal plan
curl -X GET "$API_BASE_URL/plan/plan_abc123" \
  -H "$AUTH_HEADER"

# Response includes full meal plan details:
# {
#   "plan_id": "plan_abc123",
#   "user_id": "user_123456",
#   "week_start": "2024-10-14",
#   "generated_at": "2024-10-13T15:30:00Z",
#   "estimated_cost": 89.45,
#   "total_calories": 8400,
#   "meals": [
#     {
#       "meal_id": "meal_789",
#       "day": "monday",
#       "meal_type": "breakfast",
#       "title": "Mediterranean Quinoa Bowl",
#       "description": "A nutritious start to your day...",
#       "ingredients": ["quinoa", "tomatoes", "cucumber", "feta"],
#       "calories": 420,
#       "prep_minutes": 15,
#       "macros": {
#         "protein": 18,
#         "carbs": 52,
#         "fat": 14,
#         "fiber": 8
#       },
#       "cost": 6.50,
#       "tags": ["vegetarian", "high_protein", "quick"]
#     }
#   ],
#   "grocery_list": [...]
# }
```

### Submit Meal Feedback

```bash
# Submit positive feedback
curl -X POST "$API_BASE_URL/plan/plan_abc123/feedback" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "plan_id": "plan_abc123",
    "meal_id": "meal_789",
    "rating": 5,
    "emoji": "😋",
    "comment": "Absolutely delicious! Perfect seasoning and easy to make."
  }'
```

```bash
# Submit critical feedback
curl -X POST "$API_BASE_URL/plan/plan_abc123/feedback" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "plan_id": "plan_abc123",
    "meal_id": "meal_456",
    "rating": 2,
    "emoji": "😕",
    "comment": "Too salty and took much longer than estimated prep time."
  }'
```

## Community Features

### Join a Crew

```bash
# Join weight loss crew
curl -X POST "$API_BASE_URL/community/crews/join" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "crew_type": "weight_loss",
    "goals": ["lose_weight", "eat_healthier", "exercise_more"]
  }'

# Response:
# {
#   "success": true,
#   "crew_id": "crew_wl_456",
#   "message": "Welcome to the Weight Loss Warriors crew!",
#   "crew_info": {
#     "name": "Weight Loss Warriors",
#     "description": "A supportive community for sustainable weight loss",
#     "member_count": 1247,
#     "average_progress": "2.3 lbs/week",
#     "success_stories": 89
#   }
# }
```

```bash
# Join muscle gain crew
curl -X POST "$API_BASE_URL/community/crews/join" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "crew_type": "muscle_gain",
    "goals": ["build_muscle", "increase_protein", "strength_training"]
  }'
```

### Submit Personal Reflection

```bash
# Daily reflection
curl -X POST "$API_BASE_URL/community/reflections" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "reflection_type": "daily",
    "content": "Today I managed to stick to my meal plan and felt more energetic throughout the day. The Mediterranean quinoa bowl was particularly satisfying!",
    "tags": ["energy", "adherence", "satisfaction"],
    "mood_score": 4
  }'
```

```bash
# Weekly reflection
curl -X POST "$API_BASE_URL/community/reflections" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "reflection_type": "weekly",
    "content": "This week was challenging with travel, but I learned to make better choices when eating out. The meal prep on Sunday really helped me stay on track.",
    "tags": ["travel", "meal_prep", "learning"],
    "mood_score": 3
  }'
```

### Get Crew Pulse

```bash
# Get crew activity and sentiment
curl -X GET "$API_BASE_URL/community/crews/crew_wl_456/pulse" \
  -H "$AUTH_HEADER"

# Response:
# {
#   "crew_id": "crew_wl_456",
#   "pulse_data": {
#     "activity_level": "high",
#     "sentiment_score": 4.2,
#     "engagement_trends": {
#       "daily_reflections": 847,
#       "weekly_reflections": 203,
#       "peer_interactions": 1456
#     },
#     "recent_highlights": [
#       "Sarah lost 5 lbs this week!",
#       "Mike completed his first 5K run",
#       "The crew has collectively lost 847 lbs!"
#     ]
#   }
# }
```

## Gamification

### Get Gamification Summary

```bash
# Get complete gamification status
curl -X GET "$API_BASE_URL/gamification/summary?user_id=$USER_ID" \
  -H "$AUTH_HEADER"

# Response:
# {
#   "user_id": "user_123456",
#   "level": 7,
#   "total_points": 2450,
#   "points_to_next_level": 550,
#   "rank": 42,
#   "total_users": 10000,
#   "adherence_ring": {
#     "percentage": 85.5,
#     "streak_days": 12,
#     "color": "green"
#   },
#   "current_streak": {
#     "type": "meal_plan_adherence",
#     "current_days": 12,
#     "longest_streak": 18,
#     "progress_percentage": 66.7
#   },
#   "active_challenge": {
#     "challenge_id": "challenge_789",
#     "title": "30-Day Meal Prep Master",
#     "description": "Prepare meals in advance for 30 consecutive days",
#     "progress": 0.4,
#     "days_remaining": 18,
#     "reward_points": 500
#   },
#   "recent_achievements": [
#     {
#       "achievement_id": "ach_001",
#       "title": "Feedback Champion",
#       "description": "Provided feedback for 50 meals",
#       "points": 100,
#       "unlocked_at": "2024-10-12T09:15:00Z"
#     }
#   ]
# }
```

### Update Progress

```bash
# Update weight progress
curl -X POST "$API_BASE_URL/gamification/progress" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "metric_type": "weight",
    "value": 165.2
  }'
```

```bash
# Update exercise progress
curl -X POST "$API_BASE_URL/gamification/progress" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "'$USER_ID'",
    "metric_type": "exercise_minutes",
    "value": 45
  }'
```

### Get Achievements

```bash
# Get all unlocked achievements
curl -X GET "$API_BASE_URL/gamification/achievements?user_id=$USER_ID&status=unlocked" \
  -H "$AUTH_HEADER"

# Get available achievements to unlock
curl -X GET "$API_BASE_URL/gamification/achievements?user_id=$USER_ID&status=available" \
  -H "$AUTH_HEADER"
```

### Get Leaderboard

```bash
# Points leaderboard
curl -X GET "$API_BASE_URL/gamification/leaderboard?type=points&limit=10" \
  -H "$AUTH_HEADER"

# Adherence leaderboard
curl -X GET "$API_BASE_URL/gamification/leaderboard?type=adherence&limit=20" \
  -H "$AUTH_HEADER"

# Weekly streak leaderboard
curl -X GET "$API_BASE_URL/gamification/leaderboard?type=streak&limit=5" \
  -H "$AUTH_HEADER"
```

## Analytics

### Track Events

```bash
# Track meal preparation event
curl -X POST "$API_BASE_URL/analytics/events" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "event_type": "meal_prepared",
    "user_id": "'$USER_ID'",
    "timestamp": "2024-10-13T18:30:00Z",
    "properties": {
      "meal_id": "meal_789",
      "prep_time_actual": 25,
      "prep_time_estimated": 30,
      "difficulty_rating": 3,
      "satisfaction_score": 4.5,
      "modifications_made": ["reduced_salt", "added_herbs"]
    }
  }'
```

```bash
# Track grocery shopping event
curl -X POST "$API_BASE_URL/analytics/events" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "event_type": "grocery_shopping_completed",
    "user_id": "'$USER_ID'",
    "timestamp": "2024-10-13T14:15:00Z",
    "properties": {
      "plan_id": "plan_abc123",
      "total_cost": 89.45,
      "budget_variance": -10.55,
      "items_purchased": 23,
      "items_substituted": 2,
      "store_type": "supermarket",
      "shopping_duration_minutes": 45
    }
  }'
```

```bash
# Track app usage event
curl -X POST "$API_BASE_URL/analytics/events" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "event_type": "app_session",
    "user_id": "'$USER_ID'",
    "timestamp": "2024-10-13T08:00:00Z",
    "properties": {
      "session_duration_minutes": 12,
      "features_used": ["meal_planning", "community", "progress_tracking"],
      "actions_completed": 5,
      "platform": "mobile_ios"
    }
  }'
```

### Get Dashboard Data

```bash
# Get analytics dashboard for date range
curl -X GET "$API_BASE_URL/analytics/dashboard?start_date=2024-10-01T00:00:00Z&end_date=2024-10-13T23:59:59Z" \
  -H "$AUTH_HEADER"

# Get current week dashboard
curl -X GET "$API_BASE_URL/analytics/dashboard" \
  -H "$AUTH_HEADER"
```

### Get User Insights

```bash
# Get personalized insights for user
curl -X GET "$API_BASE_URL/analytics/users/$USER_ID/insights" \
  -H "$AUTH_HEADER"

# Response:
# {
#   "user_id": "user_123456",
#   "insights": {
#     "meal_prep_patterns": {
#       "preferred_prep_day": "sunday",
#       "average_prep_time": 28,
#       "success_rate": 0.85
#     },
#     "engagement_trends": {
#       "most_active_time": "evening",
#       "weekly_sessions": 4.2,
#       "feature_preferences": ["meal_planning", "progress_tracking"]
#     },
#     "nutrition_progress": {
#       "calorie_adherence": 0.92,
#       "macro_balance_score": 4.1,
#       "improvement_areas": ["protein_intake", "meal_timing"]
#     }
#   }
# }
```

## Integrations

### Calendar Integration

```bash
# Initiate Google Calendar OAuth
curl -X POST "$API_BASE_URL/integrations/calendar/auth" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "provider": "google",
    "redirect_uri": "https://myapp.com/integrations/calendar/callback"
  }'

# Response includes OAuth URL:
# {
#   "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
#   "state": "random_state_string"
# }
```

```bash
# Create calendar events for meal plan
curl -X POST "$API_BASE_URL/integrations/calendar/events" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "meal_plan_id": "plan_abc123",
    "prep_time_minutes": 30,
    "cook_time_minutes": 45,
    "send_reminders": true
  }'
```

### Fitness Data Sync

```bash
# Sync fitness data from connected devices
curl -X POST "$API_BASE_URL/integrations/fitness/sync" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "date": "2024-10-13"
  }'
```

```bash
# Sync all available fitness data
curl -X POST "$API_BASE_URL/integrations/fitness/sync" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{}'
```

### Grocery Store Integrations

```bash
# Get grocery store deep links
curl -X POST "$API_BASE_URL/integrations/grocery/deeplinks" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "grocery_list_id": "plan_abc123",
    "preferred_partners": ["instacart", "amazon_fresh", "walmart"]
  }'

# Response:
# {
#   "deeplinks": {
#     "instacart": "https://instacart.com/store/add-to-cart?items=...",
#     "amazon_fresh": "https://fresh.amazon.com/cart/add?asin=...",
#     "walmart": "https://walmart.com/grocery/cart?items=..."
#   },
#   "estimated_costs": {
#     "instacart": 92.50,
#     "amazon_fresh": 89.99,
#     "walmart": 85.75
#   },
#   "availability": {
#     "instacart": "same_day",
#     "amazon_fresh": "next_day",
#     "walmart": "2_hour_pickup"
#   }
# }
```

## Infrastructure

### Health Check

```bash
# Basic health check
curl -X GET "$API_BASE_URL/health" \
  -H "$AUTH_HEADER"

# Response:
# {
#   "status": "healthy",
#   "timestamp": "2024-10-13T15:30:00Z",
#   "version": "2.1.0",
#   "uptime": "72h 15m 30s"
# }
```

### Detailed System Status

```bash
# Comprehensive health check
curl -X GET "$API_BASE_URL/health/detailed" \
  -H "$AUTH_HEADER"

# Response:
# {
#   "status": "healthy",
#   "timestamp": "2024-10-13T15:30:00Z",
#   "version": "2.1.0",
#   "uptime": "72h 15m 30s",
#   "services": {
#     "database": {
#       "status": "healthy",
#       "response_time_ms": 15,
#       "connection_pool": {
#         "active": 5,
#         "idle": 10,
#         "max": 20
#       }
#     },
#     "ai_service": {
#       "status": "healthy",
#       "response_time_ms": 250,
#       "queue_size": 3
#     },
#     "cache": {
#       "status": "healthy",
#       "hit_rate": 0.87,
#       "memory_usage": "45%"
#     }
#   },
#   "metrics": {
#     "requests_per_minute": 150,
#     "error_rate": 0.01,
#     "average_response_time_ms": 120
#   }
# }
```

### Metrics

```bash
# Get system metrics
curl -X GET "$API_BASE_URL/metrics" \
  -H "$AUTH_HEADER"
```

## Error Handling

### Rate Limit Example

```bash
# This request will demonstrate rate limiting
for i in {1..20}; do
  echo "Request $i:"
  curl -X GET "$API_BASE_URL/health" \
    -H "$AUTH_HEADER" \
    -w "Status: %{http_code}, Time: %{time_total}s\n" \
    -s -o /dev/null
  sleep 0.1
done

# When rate limited, you'll see:
# Status: 429, Time: 0.05s
# Response headers will include:
# Retry-After: 60
# X-RateLimit-Remaining: 0
# X-RateLimit-Reset: 1697200800
```

### Error Response Example

```bash
# Invalid request that will return error
curl -X POST "$API_BASE_URL/plan/generate" \
  -H "$CONTENT_TYPE" \
  -H "$AUTH_HEADER" \
  -d '{
    "user_id": "",
    "preferences": {
      "budget_per_week": -50
    }
  }'

# Error response:
# {
#   "error": {
#     "code": "validation_error",
#     "message": "Request validation failed",
#     "details": [
#       {
#         "field": "user_id",
#         "message": "Field required"
#       },
#       {
#         "field": "preferences.budget_per_week",
#         "message": "Value must be greater than 0"
#       }
#     ]
#   },
#   "request_id": "req_abc123def456"
# }
```

## Bash Scripts

### Authentication Script

```bash
#!/bin/bash
# auth.sh - Handle authentication flow

API_BASE_URL=${API_BASE_URL:-"https://api.ai-nutritionist.com/v1"}
PHONE_NUMBER=${1:-"+1234567890"}

echo "🔐 Starting authentication for $PHONE_NUMBER"

# Step 1: Send verification code
echo "📱 Sending verification code..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"channel\": \"sms\", \"identifier\": \"$PHONE_NUMBER\"}")

if [[ $(echo $LOGIN_RESPONSE | jq -r '.success') == "true" ]]; then
  echo "✅ Verification code sent successfully"
  EXPIRES_IN=$(echo $LOGIN_RESPONSE | jq -r '.expires_in')
  echo "⏰ Code expires in $EXPIRES_IN seconds"

  # Step 2: Get verification code from user
  echo "Enter the verification code:"
  read -r VERIFICATION_CODE

  # Step 3: Verify the code
  echo "🔍 Verifying code..."
  VERIFY_RESPONSE=$(curl -s -X POST "$API_BASE_URL/auth/verify" \
    -H "Content-Type: application/json" \
    -d "{\"identifier\": \"$PHONE_NUMBER\", \"code\": \"$VERIFICATION_CODE\"}")

  if [[ $(echo $VERIFY_RESPONSE | jq -r '.success') == "true" ]]; then
    ACCESS_TOKEN=$(echo $VERIFY_RESPONSE | jq -r '.access_token')
    REFRESH_TOKEN=$(echo $VERIFY_RESPONSE | jq -r '.refresh_token')
    USER_ID=$(echo $VERIFY_RESPONSE | jq -r '.user.user_id')

    echo "🎉 Authentication successful!"
    echo "💾 Saving tokens to .env file"

    # Save to environment file
    cat > .env << EOF
API_BASE_URL=$API_BASE_URL
API_TOKEN=$ACCESS_TOKEN
REFRESH_TOKEN=$REFRESH_TOKEN
USER_ID=$USER_ID
AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
EOF

    echo "✅ Authentication complete. Tokens saved to .env"
    echo "🔑 User ID: $USER_ID"

  else
    echo "❌ Verification failed"
    echo $VERIFY_RESPONSE | jq .
    exit 1
  fi
else
  echo "❌ Failed to send verification code"
  echo $LOGIN_RESPONSE | jq .
  exit 1
fi
```

### Meal Plan Generator Script

```bash
#!/bin/bash
# generate_plan.sh - Generate and display meal plan

source .env

DIETARY_RESTRICTIONS=${1:-"vegetarian"}
BUDGET=${2:-120.00}
SERVINGS=${3:-4}

echo "🥗 Generating meal plan..."
echo "   Dietary restrictions: $DIETARY_RESTRICTIONS"
echo "   Budget: \$$BUDGET"
echo "   Servings: $SERVINGS"

PLAN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/plan/generate" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"preferences\": {
      \"dietary_restrictions\": [\"$DIETARY_RESTRICTIONS\"],
      \"budget_per_week\": $BUDGET,
      \"servings\": $SERVINGS,
      \"prep_time_preference\": \"moderate\"
    }
  }")

if [[ $(echo $PLAN_RESPONSE | jq -r '.plan_id') != "null" ]]; then
  PLAN_ID=$(echo $PLAN_RESPONSE | jq -r '.plan_id')
  ESTIMATED_COST=$(echo $PLAN_RESPONSE | jq -r '.estimated_cost')
  TOTAL_CALORIES=$(echo $PLAN_RESPONSE | jq -r '.total_calories')
  MEAL_COUNT=$(echo $PLAN_RESPONSE | jq -r '.meals | length')

  echo "✅ Plan generated successfully!"
  echo "📋 Plan ID: $PLAN_ID"
  echo "💰 Estimated cost: \$$ESTIMATED_COST"
  echo "🔥 Total calories: $TOTAL_CALORIES"
  echo "🍽️  Number of meals: $MEAL_COUNT"

  echo ""
  echo "📅 Meal Schedule:"
  echo $PLAN_RESPONSE | jq -r '.meals[] | "  \(.day | ascii_upcase) \(.meal_type | ascii_upcase): \(.title) (\(.calories) cal, \(.prep_minutes) min, $\(.cost))"'

  # Save plan ID for future use
  echo "PLAN_ID=$PLAN_ID" >> .env

else
  echo "❌ Failed to generate plan"
  echo $PLAN_RESPONSE | jq .
  exit 1
fi
```

### Feedback Submission Script

```bash
#!/bin/bash
# submit_feedback.sh - Submit meal feedback

source .env

MEAL_ID=${1}
RATING=${2:-5}
EMOJI=${3:-"😋"}
COMMENT=${4:-"Great meal!"}

if [[ -z "$MEAL_ID" ]]; then
  echo "Usage: $0 <meal_id> [rating] [emoji] [comment]"
  echo "Example: $0 meal_789 4 😊 'Good but a bit salty'"
  exit 1
fi

echo "⭐ Submitting feedback for meal $MEAL_ID"
echo "   Rating: $RATING/5"
echo "   Emoji: $EMOJI"
echo "   Comment: $COMMENT"

FEEDBACK_RESPONSE=$(curl -s -X POST "$API_BASE_URL/plan/$PLAN_ID/feedback" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"plan_id\": \"$PLAN_ID\",
    \"meal_id\": \"$MEAL_ID\",
    \"rating\": $RATING,
    \"emoji\": \"$EMOJI\",
    \"comment\": \"$COMMENT\"
  }")

if [[ $(echo $FEEDBACK_RESPONSE | jq -r '.success') == "true" ]]; then
  echo "✅ Feedback submitted successfully!"
  echo "📝 $(echo $FEEDBACK_RESPONSE | jq -r '.message')"
else
  echo "❌ Failed to submit feedback"
  echo $FEEDBACK_RESPONSE | jq .
  exit 1
fi
```

### Analytics Tracking Script

```bash
#!/bin/bash
# track_event.sh - Track analytics events

source .env

EVENT_TYPE=${1}
PROPERTIES=${2:-"{}"}

if [[ -z "$EVENT_TYPE" ]]; then
  echo "Usage: $0 <event_type> [properties_json]"
  echo "Example: $0 meal_prepared '{\"meal_id\": \"meal_789\", \"prep_time_actual\": 25}'"
  exit 1
fi

echo "📊 Tracking event: $EVENT_TYPE"

TRACK_RESPONSE=$(curl -s -X POST "$API_BASE_URL/analytics/events" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{
    \"event_type\": \"$EVENT_TYPE\",
    \"user_id\": \"$USER_ID\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"properties\": $PROPERTIES
  }")

if [[ $(echo $TRACK_RESPONSE | jq -r '.success') == "true" ]]; then
  echo "✅ Event tracked successfully!"
else
  echo "❌ Failed to track event"
  echo $TRACK_RESPONSE | jq .
  exit 1
fi
```

### System Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Monitor API health and performance

source .env

echo "🔍 AI Nutritionist API Health Monitor"
echo "======================================"

# Basic health check
echo "1. Basic Health Check"
HEALTH_RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" "$API_BASE_URL/health")
HTTP_STATUS=$(echo $HEALTH_RESPONSE | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
RESPONSE_TIME=$(echo $HEALTH_RESPONSE | grep -o "TIME:[0-9.]*" | cut -d: -f2)
HEALTH_BODY=$(echo $HEALTH_RESPONSE | sed -E 's/HTTPSTATUS:[0-9]*;TIME:[0-9.]*$//')

if [[ $HTTP_STATUS -eq 200 ]]; then
  echo "   ✅ API is healthy (${RESPONSE_TIME}s)"
  echo "   📊 $(echo $HEALTH_BODY | jq -r '.status') - $(echo $HEALTH_BODY | jq -r '.version')"
else
  echo "   ❌ API health check failed (HTTP $HTTP_STATUS)"
fi

# Detailed health check
echo ""
echo "2. Detailed System Status"
DETAILED_RESPONSE=$(curl -s "$API_BASE_URL/health/detailed" -H "$AUTH_HEADER")

if [[ $(echo $DETAILED_RESPONSE | jq -r '.status') == "healthy" ]]; then
  echo "   ✅ All services operational"

  # Database status
  DB_STATUS=$(echo $DETAILED_RESPONSE | jq -r '.services.database.status')
  DB_RESPONSE_TIME=$(echo $DETAILED_RESPONSE | jq -r '.services.database.response_time_ms')
  echo "   💾 Database: $DB_STATUS (${DB_RESPONSE_TIME}ms)"

  # AI service status
  AI_STATUS=$(echo $DETAILED_RESPONSE | jq -r '.services.ai_service.status')
  AI_RESPONSE_TIME=$(echo $DETAILED_RESPONSE | jq -r '.services.ai_service.response_time_ms')
  echo "   🤖 AI Service: $AI_STATUS (${AI_RESPONSE_TIME}ms)"

  # Cache status
  CACHE_STATUS=$(echo $DETAILED_RESPONSE | jq -r '.services.cache.status')
  CACHE_HIT_RATE=$(echo $DETAILED_RESPONSE | jq -r '.services.cache.hit_rate')
  echo "   📦 Cache: $CACHE_STATUS (${CACHE_HIT_RATE} hit rate)"

  # Performance metrics
  RPM=$(echo $DETAILED_RESPONSE | jq -r '.metrics.requests_per_minute')
  ERROR_RATE=$(echo $DETAILED_RESPONSE | jq -r '.metrics.error_rate')
  AVG_RESPONSE=$(echo $DETAILED_RESPONSE | jq -r '.metrics.average_response_time_ms')

  echo ""
  echo "3. Performance Metrics"
  echo "   📈 Requests/min: $RPM"
  echo "   ⚠️  Error rate: $(echo "$ERROR_RATE * 100" | bc -l | cut -c1-5)%"
  echo "   ⏱️  Avg response: ${AVG_RESPONSE}ms"

else
  echo "   ❌ System issues detected"
  echo $DETAILED_RESPONSE | jq .
fi

# Test authentication
echo ""
echo "4. Authentication Test"
AUTH_TEST=$(curl -s -w "HTTPSTATUS:%{http_code}" "$API_BASE_URL/gamification/summary?user_id=$USER_ID" -H "$AUTH_HEADER")
AUTH_STATUS=$(echo $AUTH_TEST | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)

if [[ $AUTH_STATUS -eq 200 ]]; then
  echo "   ✅ Authentication working"
elif [[ $AUTH_STATUS -eq 401 ]]; then
  echo "   ⚠️  Authentication failed - token may be expired"
elif [[ $AUTH_STATUS -eq 429 ]]; then
  echo "   ⚠️  Rate limited"
else
  echo "   ❌ Authentication test failed (HTTP $AUTH_STATUS)"
fi

echo ""
echo "Monitor complete at $(date)"
```

### Rate Limit Testing Script

```bash
#!/bin/bash
# rate_limit_test.sh - Test API rate limits

source .env

ENDPOINT=${1:-"/health"}
REQUESTS=${2:-20}
INTERVAL=${3:-0.1}

echo "🚦 Testing rate limits for $ENDPOINT"
echo "   Requests: $REQUESTS"
echo "   Interval: ${INTERVAL}s"
echo ""

SUCCESS_COUNT=0
RATE_LIMITED_COUNT=0

for i in $(seq 1 $REQUESTS); do
  RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" \
    "$API_BASE_URL$ENDPOINT" -H "$AUTH_HEADER")

  HTTP_STATUS=$(echo $RESPONSE | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
  RESPONSE_TIME=$(echo $RESPONSE | grep -o "TIME:[0-9.]*" | cut -d: -f2)

  if [[ $HTTP_STATUS -eq 200 ]]; then
    echo "Request $i: ✅ Success (${RESPONSE_TIME}s)"
    ((SUCCESS_COUNT++))
  elif [[ $HTTP_STATUS -eq 429 ]]; then
    echo "Request $i: ⚠️  Rate limited"
    ((RATE_LIMITED_COUNT++))
  else
    echo "Request $i: ❌ Error (HTTP $HTTP_STATUS)"
  fi

  sleep $INTERVAL
done

echo ""
echo "📊 Results:"
echo "   ✅ Successful: $SUCCESS_COUNT"
echo "   ⚠️  Rate limited: $RATE_LIMITED_COUNT"
echo "   ❌ Errors: $((REQUESTS - SUCCESS_COUNT - RATE_LIMITED_COUNT))"
```

### Complete Integration Test

```bash
#!/bin/bash
# integration_test.sh - Complete API integration test

source .env

echo "🧪 AI Nutritionist API Integration Test"
echo "======================================"

TEST_USER_ID="test_user_$(date +%s)"
SUCCESS_COUNT=0
TOTAL_TESTS=8

test_result() {
  if [[ $1 -eq 0 ]]; then
    echo "   ✅ $2"
    ((SUCCESS_COUNT++))
  else
    echo "   ❌ $2"
  fi
}

# Test 1: Health check
echo ""
echo "Test 1: Health Check"
curl -s "$API_BASE_URL/health" | jq -e '.status == "healthy"' > /dev/null
test_result $? "Health check passed"

# Test 2: Generate meal plan
echo ""
echo "Test 2: Generate Meal Plan"
PLAN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/plan/generate" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{\"user_id\": \"$TEST_USER_ID\", \"preferences\": {\"budget_per_week\": 100}}")

PLAN_ID=$(echo $PLAN_RESPONSE | jq -r '.plan_id')
[[ "$PLAN_ID" != "null" && -n "$PLAN_ID" ]]
test_result $? "Meal plan generation"

# Test 3: Retrieve meal plan
echo ""
echo "Test 3: Retrieve Meal Plan"
curl -s "$API_BASE_URL/plan/$PLAN_ID" -H "$AUTH_HEADER" | jq -e '.plan_id == "'$PLAN_ID'"' > /dev/null
test_result $? "Meal plan retrieval"

# Test 4: Submit feedback
echo ""
echo "Test 4: Submit Feedback"
FIRST_MEAL_ID=$(echo $PLAN_RESPONSE | jq -r '.meals[0].meal_id')
FEEDBACK_RESPONSE=$(curl -s -X POST "$API_BASE_URL/plan/$PLAN_ID/feedback" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{\"user_id\": \"$TEST_USER_ID\", \"plan_id\": \"$PLAN_ID\", \"meal_id\": \"$FIRST_MEAL_ID\", \"rating\": 5}")

echo $FEEDBACK_RESPONSE | jq -e '.success == true' > /dev/null
test_result $? "Feedback submission"

# Test 5: Join crew
echo ""
echo "Test 5: Join Community Crew"
CREW_RESPONSE=$(curl -s -X POST "$API_BASE_URL/community/crews/join" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{\"user_id\": \"$TEST_USER_ID\", \"crew_type\": \"weight_loss\"}")

echo $CREW_RESPONSE | jq -e '.success == true' > /dev/null
test_result $? "Community crew join"

# Test 6: Submit reflection
echo ""
echo "Test 6: Submit Reflection"
REFLECTION_RESPONSE=$(curl -s -X POST "$API_BASE_URL/community/reflections" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{\"user_id\": \"$TEST_USER_ID\", \"reflection_type\": \"daily\", \"content\": \"Test reflection\"}")

echo $REFLECTION_RESPONSE | jq -e '.reflection_id != null' > /dev/null
test_result $? "Reflection submission"

# Test 7: Get gamification summary
echo ""
echo "Test 7: Gamification Summary"
curl -s "$API_BASE_URL/gamification/summary?user_id=$TEST_USER_ID" -H "$AUTH_HEADER" | jq -e '.user_id == "'$TEST_USER_ID'"' > /dev/null
test_result $? "Gamification summary"

# Test 8: Track analytics event
echo ""
echo "Test 8: Track Analytics Event"
ANALYTICS_RESPONSE=$(curl -s -X POST "$API_BASE_URL/analytics/events" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{\"event_type\": \"integration_test\", \"user_id\": \"$TEST_USER_ID\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}")

echo $ANALYTICS_RESPONSE | jq -e '.success == true' > /dev/null
test_result $? "Analytics event tracking"

# Results
echo ""
echo "🏁 Integration Test Complete"
echo "=============================="
echo "✅ Passed: $SUCCESS_COUNT/$TOTAL_TESTS"
echo "❌ Failed: $((TOTAL_TESTS - SUCCESS_COUNT))/$TOTAL_TESTS"

if [[ $SUCCESS_COUNT -eq $TOTAL_TESTS ]]; then
  echo "🎉 All tests passed!"
  exit 0
else
  echo "⚠️  Some tests failed"
  exit 1
fi
```

## Usage Instructions

1. **Set up environment**: Copy the environment setup section and modify with your API credentials
2. **Make scripts executable**: `chmod +x *.sh`
3. **Run authentication**: `./auth.sh +1234567890`
4. **Generate meal plans**: `./generate_plan.sh vegetarian 120 4`
5. **Submit feedback**: `./submit_feedback.sh meal_789 5 😋 "Delicious!"`
6. **Monitor system**: `./monitor.sh`
7. **Run integration tests**: `./integration_test.sh`

These cURL examples and scripts provide a comprehensive foundation for integrating with and testing the AI Nutritionist API.
