# Python Client Examples

This guide provides comprehensive Python examples for integrating with the AI Nutritionist API.

## Installation

```bash
pip install ai-nutritionist-api requests pydantic
```

## Basic Setup

```python
import os
import requests
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel

class AIGenome_Client:
    """AI Nutritionist API Client"""

    def __init__(self, base_url: str = None, api_token: str = None):
        self.base_url = base_url or os.getenv('AI_NUTRITIONIST_API_URL', 'https://api.ai-nutritionist.com/v1')
        self.api_token = api_token or os.getenv('AI_NUTRITIONIST_API_TOKEN')
        self.session = requests.Session()

        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'ai-nutritionist-python/2.0.0'
            })

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with error handling"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds.")

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {e}")

    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET request"""
        response = self.request('GET', endpoint, params=params)
        return response.json()

    def post(self, endpoint: str, data: Dict = None) -> Dict:
        """POST request"""
        response = self.request('POST', endpoint, json=data)
        return response.json()

    def put(self, endpoint: str, data: Dict = None) -> Dict:
        """PUT request"""
        response = self.request('PUT', endpoint, json=data)
        return response.json()

    def delete(self, endpoint: str) -> bool:
        """DELETE request"""
        response = self.request('DELETE', endpoint)
        return response.status_code == 204

class APIError(Exception):
    """Base API exception"""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded exception"""
    pass

class AuthenticationError(APIError):
    """Authentication failed exception"""
    pass
```

## Authentication

```python
class AuthClient(AIGenome_Client):
    """Authentication client"""

    def login(self, channel: str, identifier: str) -> Dict:
        """Initiate authentication"""
        data = {
            'channel': channel,  # 'sms' or 'email'
            'identifier': identifier  # phone number or email
        }
        return self.post('auth/login', data)

    def verify(self, identifier: str, code: str) -> Dict:
        """Verify authentication code"""
        data = {
            'identifier': identifier,
            'code': code
        }
        response = self.post('auth/verify', data)

        # Update client with new token
        if 'access_token' in response:
            self.api_token = response['access_token']
            self.session.headers['Authorization'] = f"Bearer {self.api_token}"

        return response

    def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh access token"""
        data = {'refresh_token': refresh_token}
        response = self.post('auth/refresh', data)

        # Update client with new token
        if 'access_token' in response:
            self.api_token = response['access_token']
            self.session.headers['Authorization'] = f"Bearer {self.api_token}"

        return response

# Example usage
auth_client = AuthClient()

# Start authentication
login_response = auth_client.login('sms', '+1234567890')
print(f"Verification code sent. Expires in: {login_response['expires_in']} seconds")

# Verify code (you would get this from user input)
verification_code = input("Enter verification code: ")
auth_response = auth_client.verify('+1234567890', verification_code)

print(f"Authentication successful!")
print(f"Access token: {auth_response['access_token'][:20]}...")
print(f"User: {auth_response['user']}")
```

## Meal Planning

```python
from typing import Optional, List
from dataclasses import dataclass
from datetime import date

@dataclass
class PlanPreferences:
    dietary_restrictions: List[str] = None
    cuisine_preferences: List[str] = None
    budget_per_week: Optional[float] = None
    servings: int = 4
    prep_time_preference: str = "moderate"
    equipment_available: List[str] = None

@dataclass
class Meal:
    meal_id: str
    day: str
    meal_type: str
    title: str
    description: str
    ingredients: List[str]
    calories: int
    prep_minutes: int
    macros: Dict[str, float]
    cost: float
    tags: List[str]

@dataclass
class MealPlan:
    plan_id: str
    user_id: str
    week_start: date
    generated_at: datetime
    estimated_cost: float
    total_calories: int
    meals: List[Meal]
    grocery_list: List[Dict]

class MealPlanningClient(AIGenome_Client):
    """Meal planning API client"""

    def generate_plan(self, user_id: str, preferences: PlanPreferences = None,
                     week_start: date = None, force_new: bool = False) -> MealPlan:
        """Generate a new meal plan"""

        data = {
            'user_id': user_id,
            'force_new': force_new
        }

        if week_start:
            data['week_start'] = week_start.isoformat()

        if preferences:
            data['preferences'] = {
                'dietary_restrictions': preferences.dietary_restrictions or [],
                'cuisine_preferences': preferences.cuisine_preferences or [],
                'budget_per_week': preferences.budget_per_week,
                'servings': preferences.servings,
                'prep_time_preference': preferences.prep_time_preference,
                'equipment_available': preferences.equipment_available or []
            }

        response = self.post('plan/generate', data)
        return self._parse_meal_plan(response)

    def get_plan(self, plan_id: str) -> MealPlan:
        """Retrieve an existing meal plan"""
        response = self.get(f'plan/{plan_id}')
        return self._parse_meal_plan(response)

    def submit_feedback(self, user_id: str, plan_id: str, meal_id: str,
                       rating: int, emoji: str = None, comment: str = None) -> Dict:
        """Submit feedback for a meal"""
        data = {
            'user_id': user_id,
            'plan_id': plan_id,
            'meal_id': meal_id,
            'rating': rating
        }

        if emoji:
            data['emoji'] = emoji
        if comment:
            data['comment'] = comment

        return self.post(f'plan/{plan_id}/feedback', data)

    def _parse_meal_plan(self, data: Dict) -> MealPlan:
        """Parse API response into MealPlan object"""
        meals = [
            Meal(
                meal_id=meal['meal_id'],
                day=meal['day'],
                meal_type=meal['meal_type'],
                title=meal['title'],
                description=meal['description'],
                ingredients=meal['ingredients'],
                calories=meal['calories'],
                prep_minutes=meal['prep_minutes'],
                macros=meal['macros'],
                cost=meal['cost'],
                tags=meal['tags']
            )
            for meal in data['meals']
        ]

        return MealPlan(
            plan_id=data['plan_id'],
            user_id=data['user_id'],
            week_start=date.fromisoformat(data['week_start']),
            generated_at=datetime.fromisoformat(data['generated_at'].replace('Z', '+00:00')),
            estimated_cost=data['estimated_cost'],
            total_calories=data['total_calories'],
            meals=meals,
            grocery_list=data['grocery_list']
        )

# Example usage
meal_client = MealPlanningClient(api_token=auth_response['access_token'])

# Set up preferences
preferences = PlanPreferences(
    dietary_restrictions=['vegetarian', 'gluten_free'],
    cuisine_preferences=['mediterranean', 'asian'],
    budget_per_week=120.00,
    servings=4,
    prep_time_preference='quick'
)

# Generate meal plan
plan = meal_client.generate_plan(
    user_id='user_123456',
    preferences=preferences,
    week_start=date(2024, 10, 14)
)

print(f"Generated plan {plan.plan_id}")
print(f"Estimated cost: ${plan.estimated_cost:.2f}")
print(f"Total calories: {plan.total_calories}")
print(f"Number of meals: {len(plan.meals)}")

# Print first few meals
for meal in plan.meals[:3]:
    print(f"\n{meal.day.title()} {meal.meal_type.title()}: {meal.title}")
    print(f"  Calories: {meal.calories}, Prep time: {meal.prep_minutes} min")
    print(f"  Cost: ${meal.cost:.2f}")

# Submit feedback
feedback_response = meal_client.submit_feedback(
    user_id='user_123456',
    plan_id=plan.plan_id,
    meal_id=plan.meals[0].meal_id,
    rating=5,
    emoji='😋',
    comment='Absolutely delicious! Perfect seasoning.'
)

print(f"\nFeedback submitted: {feedback_response['message']}")
```

## Community Features

```python
class CommunityClient(AIGenome_Client):
    """Community API client"""

    def join_crew(self, user_id: str, crew_type: str, goals: List[str] = None) -> Dict:
        """Join a community crew"""
        data = {
            'user_id': user_id,
            'crew_type': crew_type,
            'goals': goals or []
        }
        return self.post('community/crews/join', data)

    def submit_reflection(self, user_id: str, reflection_type: str,
                         content: str, tags: List[str] = None, mood_score: int = None) -> Dict:
        """Submit a personal reflection"""
        data = {
            'user_id': user_id,
            'reflection_type': reflection_type,
            'content': content
        }

        if tags:
            data['tags'] = tags
        if mood_score:
            data['mood_score'] = mood_score

        return self.post('community/reflections', data)

    def get_crew_pulse(self, crew_id: str) -> Dict:
        """Get crew pulse metrics"""
        return self.get(f'community/crews/{crew_id}/pulse')

# Example usage
community_client = CommunityClient(api_token=auth_response['access_token'])

# Join a crew
crew_response = community_client.join_crew(
    user_id='user_123456',
    crew_type='weight_loss',
    goals=['lose_weight', 'eat_healthier', 'exercise_more']
)

print(f"Joined crew: {crew_response['crew_id']}")
print(f"Welcome message: {crew_response['message']}")

# Submit a reflection
reflection_response = community_client.submit_reflection(
    user_id='user_123456',
    reflection_type='daily',
    content='Today I managed to stick to my meal plan and felt more energetic throughout the day. The Mediterranean quinoa bowl was particularly satisfying!',
    tags=['energy', 'adherence', 'satisfaction'],
    mood_score=4
)

print(f"Reflection submitted: {reflection_response['reflection_id']}")
```

## Gamification

```python
class GamificationClient(AIGenome_Client):
    """Gamification API client"""

    def get_summary(self, user_id: str) -> Dict:
        """Get complete gamification summary"""
        params = {'user_id': user_id}
        return self.get('gamification/summary', params)

    def update_progress(self, user_id: str, metric_type: str, value: float) -> Dict:
        """Update user progress"""
        data = {
            'user_id': user_id,
            'metric_type': metric_type,
            'value': value
        }
        return self.post('gamification/progress', data)

    def get_achievements(self, user_id: str, status: str = None) -> List[Dict]:
        """Get user achievements"""
        params = {'user_id': user_id}
        if status:
            params['status'] = status

        response = self.get('gamification/achievements', params)
        return response['achievements']

    def get_leaderboard(self, board_type: str = 'points', limit: int = 10) -> List[Dict]:
        """Get leaderboard rankings"""
        params = {
            'type': board_type,
            'limit': limit
        }
        response = self.get('gamification/leaderboard', params)
        return response['rankings']

# Example usage
gamification_client = GamificationClient(api_token=auth_response['access_token'])

# Get gamification summary
summary = gamification_client.get_summary('user_123456')

print("🎮 Gamification Summary")
print(f"Level: {summary['level']}")
print(f"Total Points: {summary['total_points']}")
print(f"Rank: {summary['rank']}")
print(f"Adherence: {summary['adherence_ring']['percentage']:.1f}%")
print(f"Current Streak: {summary['current_streak']['current_days']} days")

if summary.get('active_challenge'):
    challenge = summary['active_challenge']
    print(f"Active Challenge: {challenge['title']}")
    print(f"Progress: {challenge['progress']*100:.1f}%")

# Get achievements
achievements = gamification_client.get_achievements('user_123456', status='unlocked')
print(f"\n🏆 Unlocked Achievements ({len(achievements)}):")
for achievement in achievements[:5]:
    print(f"  {achievement['title']} - {achievement['points']} points")
```

## Analytics

```python
class AnalyticsClient(AIGenome_Client):
    """Analytics API client"""

    def track_event(self, event_type: str, user_id: str, properties: Dict = None) -> Dict:
        """Track an analytics event"""
        data = {
            'event_type': event_type,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'properties': properties or {}
        }
        return self.post('analytics/events', data)

    def get_dashboard(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get analytics dashboard data"""
        params = {}
        if start_date:
            params['start_date'] = start_date.isoformat() + 'Z'
        if end_date:
            params['end_date'] = end_date.isoformat() + 'Z'

        return self.get('analytics/dashboard', params)

    def get_user_insights(self, user_id: str) -> Dict:
        """Get insights for a specific user"""
        return self.get(f'analytics/users/{user_id}/insights')

# Example usage
analytics_client = AnalyticsClient(api_token=auth_response['access_token'])

# Track custom events
analytics_client.track_event(
    event_type='meal_prepared',
    user_id='user_123456',
    properties={
        'meal_id': 'meal_789',
        'prep_time_actual': 25,
        'prep_time_estimated': 30,
        'difficulty_rating': 3,
        'satisfaction_score': 4.5
    }
)

analytics_client.track_event(
    event_type='grocery_shopping_completed',
    user_id='user_123456',
    properties={
        'plan_id': plan.plan_id,
        'total_cost': 89.45,
        'items_purchased': 23,
        'store_type': 'supermarket'
    }
)

# Get dashboard data
dashboard = analytics_client.get_dashboard()
print("\n📊 Analytics Dashboard")
print(f"Total Users: {dashboard['summary']['total_users']}")
print(f"Active Users: {dashboard['summary']['active_users']}")
print(f"Plans Generated: {dashboard['summary']['plans_generated']}")
print(f"Engagement Rate: {dashboard['summary']['engagement_rate']:.1%}")
```

## Integrations

```python
class IntegrationsClient(AIGenome_Client):
    """Integrations API client"""

    def initiate_calendar_auth(self, provider: str, redirect_uri: str) -> Dict:
        """Start calendar OAuth flow"""
        data = {
            'provider': provider,  # 'google', 'outlook', 'apple'
            'redirect_uri': redirect_uri
        }
        return self.post('integrations/calendar/auth', data)

    def create_calendar_events(self, meal_plan_id: str, prep_time_minutes: int = 30,
                              cook_time_minutes: int = 45, send_reminders: bool = True) -> Dict:
        """Create calendar events for meal prep"""
        data = {
            'meal_plan_id': meal_plan_id,
            'prep_time_minutes': prep_time_minutes,
            'cook_time_minutes': cook_time_minutes,
            'send_reminders': send_reminders
        }
        return self.post('integrations/calendar/events', data)

    def sync_fitness_data(self, date: date = None) -> Dict:
        """Sync fitness data from connected devices"""
        data = {}
        if date:
            data['date'] = date.isoformat()

        return self.post('integrations/fitness/sync', data)

    def get_grocery_deeplinks(self, grocery_list_id: str, preferred_partners: List[str] = None) -> Dict:
        """Get grocery store deep links"""
        data = {
            'grocery_list_id': grocery_list_id,
            'preferred_partners': preferred_partners or []
        }
        return self.post('integrations/grocery/deeplinks', data)

# Example usage
integrations_client = IntegrationsClient(api_token=auth_response['access_token'])

# Set up calendar integration
calendar_auth = integrations_client.initiate_calendar_auth(
    provider='google',
    redirect_uri='https://myapp.com/integrations/calendar/callback'
)

print(f"Calendar OAuth URL: {calendar_auth['authorization_url']}")

# Create calendar events for meal plan
calendar_events = integrations_client.create_calendar_events(
    meal_plan_id=plan.plan_id,
    prep_time_minutes=30,
    send_reminders=True
)

print(f"Created {calendar_events['events_created']} calendar events")

# Get grocery store links
grocery_links = integrations_client.get_grocery_deeplinks(
    grocery_list_id=plan.plan_id,  # Using plan ID as grocery list ID
    preferred_partners=['instacart', 'amazon_fresh', 'walmart']
)

print("\n🛒 Grocery Store Links:")
for store, link in grocery_links['deeplinks'].items():
    print(f"  {store.title()}: {link}")
```

## Error Handling and Retry Logic

```python
import time
import random
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    """Decorator for retrying API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt == max_retries:
                        raise

                    # Extract retry-after from error message or use backoff
                    delay = base_delay * (2 ** attempt)
                    jitter = random.uniform(0, 0.1) * delay
                    total_delay = min(delay + jitter, max_delay)

                    print(f"Rate limited. Retrying in {total_delay:.1f} seconds...")
                    time.sleep(total_delay)

                except APIError as e:
                    if attempt == max_retries:
                        raise

                    # Only retry on server errors (5xx)
                    if hasattr(e, 'status_code') and e.status_code >= 500:
                        delay = base_delay * (2 ** attempt)
                        print(f"Server error. Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator

class RobustAIGenome_Client(AIGenome_Client):
    """API client with built-in retry logic"""

    @retry_with_backoff(max_retries=3)
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with retry logic"""
        return super().request(method, endpoint, **kwargs)

# Example usage with error handling
try:
    robust_client = RobustAIGenome_Client(api_token=auth_response['access_token'])

    # This will automatically retry on rate limits and server errors
    plan = robust_client.generate_plan(
        user_id='user_123456',
        preferences=preferences
    )

except RateLimitError:
    print("Rate limit exceeded after all retries")
except AuthenticationError:
    print("Authentication failed. Please re-authenticate.")
except APIError as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Async Support

```python
import asyncio
import aiohttp
from typing import AsyncGenerator

class AsyncAIGenome_Client:
    """Async AI Nutritionist API Client"""

    def __init__(self, base_url: str = None, api_token: str = None):
        self.base_url = base_url or os.getenv('AI_NUTRITIONIST_API_URL', 'https://api.ai-nutritionist.com/v1')
        self.api_token = api_token or os.getenv('AI_NUTRITIONIST_API_TOKEN')
        self.session = None

    async def __aenter__(self):
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'ai-nutritionist-python-async/2.0.0'
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def request(self, method: str, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make async API request"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        async with self.session.request(method, url, **kwargs) as response:
            if response.status == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds.")

            response.raise_for_status()
            return await response.json()

    async def generate_multiple_plans(self, user_requests: List[Dict]) -> List[MealPlan]:
        """Generate multiple meal plans concurrently"""
        tasks = [
            self.request('POST', 'plan/generate', json=request)
            for request in user_requests
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        plans = []
        for response in responses:
            if isinstance(response, Exception):
                print(f"Plan generation failed: {response}")
                continue
            plans.append(self._parse_meal_plan(response))

        return plans

# Example async usage
async def main():
    async with AsyncAIGenome_Client(api_token=auth_response['access_token']) as client:
        # Generate multiple plans concurrently
        user_requests = [
            {
                'user_id': f'user_{i}',
                'preferences': {
                    'dietary_restrictions': ['vegetarian'],
                    'budget_per_week': 100 + (i * 20),
                    'servings': 2 + i
                }
            }
            for i in range(5)
        ]

        plans = await client.generate_multiple_plans(user_requests)

        for i, plan in enumerate(plans):
            print(f"Plan {i+1}: ${plan.estimated_cost:.2f}, {len(plan.meals)} meals")

# Run async example
# asyncio.run(main())
```

## Configuration and Environment Management

```python
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class APIConfig:
    """API configuration settings"""
    base_url: str = field(default_factory=lambda: os.getenv('AI_NUTRITIONIST_API_URL', 'https://api.ai-nutritionist.com/v1'))
    api_token: Optional[str] = field(default_factory=lambda: os.getenv('AI_NUTRITIONIST_API_TOKEN'))
    timeout: int = field(default_factory=lambda: int(os.getenv('API_TIMEOUT', '30')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('API_MAX_RETRIES', '3')))
    debug: bool = field(default_factory=lambda: os.getenv('API_DEBUG', 'false').lower() == 'true')

class ConfiguredClient(AIGenome_Client):
    """Client with configuration management"""

    def __init__(self, config: APIConfig = None):
        self.config = config or APIConfig()
        super().__init__(
            base_url=self.config.base_url,
            api_token=self.config.api_token
        )

        # Set timeout
        self.session.timeout = self.config.timeout

        # Enable debug logging if requested
        if self.config.debug:
            import logging
            logging.basicConfig(level=logging.DEBUG)

# Example with configuration
config = APIConfig(
    base_url='https://staging-api.ai-nutritionist.com/v1',
    timeout=60,
    debug=True
)

client = ConfiguredClient(config)
```

## Complete Example Application

```python
#!/usr/bin/env python3
"""
AI Nutritionist Python Client Example Application
"""

def main():
    print("🥗 AI Nutritionist Python Client Example")
    print("=" * 50)

    # 1. Authentication
    print("\n1. Authentication")
    auth_client = AuthClient()

    # For demo purposes, we'll skip actual SMS verification
    # In real usage, you would collect the verification code from user input

    # Simulate successful authentication
    api_token = os.getenv('AI_NUTRITIONIST_API_TOKEN')
    if not api_token:
        print("Please set AI_NUTRITIONIST_API_TOKEN environment variable")
        return

    print("✅ Authentication successful")

    # 2. Generate Meal Plan
    print("\n2. Generating Meal Plan")
    meal_client = MealPlanningClient(api_token=api_token)

    preferences = PlanPreferences(
        dietary_restrictions=['vegetarian'],
        cuisine_preferences=['mediterranean', 'asian'],
        budget_per_week=120.00,
        servings=4,
        prep_time_preference='moderate'
    )

    try:
        plan = meal_client.generate_plan(
            user_id='demo_user_123',
            preferences=preferences
        )

        print(f"✅ Generated plan {plan.plan_id}")
        print(f"   Estimated cost: ${plan.estimated_cost:.2f}")
        print(f"   Total calories: {plan.total_calories}")
        print(f"   Number of meals: {len(plan.meals)}")

        # Show a few meals
        print("\n   Sample meals:")
        for meal in plan.meals[:3]:
            print(f"   • {meal.day.title()} {meal.meal_type.title()}: {meal.title}")
            print(f"     {meal.calories} cal, {meal.prep_minutes} min, ${meal.cost:.2f}")

    except Exception as e:
        print(f"❌ Plan generation failed: {e}")
        return

    # 3. Submit Feedback
    print("\n3. Submitting Feedback")
    try:
        feedback = meal_client.submit_feedback(
            user_id='demo_user_123',
            plan_id=plan.plan_id,
            meal_id=plan.meals[0].meal_id,
            rating=5,
            emoji='😋',
            comment='Delicious and easy to make!'
        )
        print(f"✅ Feedback submitted: {feedback['message']}")
    except Exception as e:
        print(f"❌ Feedback submission failed: {e}")

    # 4. Community Features
    print("\n4. Community Features")
    community_client = CommunityClient(api_token=api_token)

    try:
        # Join crew
        crew_response = community_client.join_crew(
            user_id='demo_user_123',
            crew_type='weight_loss',
            goals=['lose_weight', 'eat_healthier']
        )
        print(f"✅ Joined crew: {crew_response['message']}")

        # Submit reflection
        reflection = community_client.submit_reflection(
            user_id='demo_user_123',
            reflection_type='daily',
            content='Great progress today! Stuck to my meal plan and feeling energetic.',
            tags=['progress', 'energy'],
            mood_score=4
        )
        print(f"✅ Reflection shared: {reflection['reflection_id']}")

    except Exception as e:
        print(f"❌ Community action failed: {e}")

    # 5. Gamification
    print("\n5. Gamification Status")
    gamification_client = GamificationClient(api_token=api_token)

    try:
        summary = gamification_client.get_summary('demo_user_123')

        print(f"✅ Level: {summary['level']}")
        print(f"   Total Points: {summary['total_points']}")
        print(f"   Current Rank: {summary['rank']}")
        print(f"   Adherence: {summary['adherence_ring']['percentage']:.1f}%")
        print(f"   Streak: {summary['current_streak']['current_days']} days")

    except Exception as e:
        print(f"❌ Gamification data unavailable: {e}")

    # 6. Analytics
    print("\n6. Analytics Tracking")
    analytics_client = AnalyticsClient(api_token=api_token)

    try:
        analytics_client.track_event(
            event_type='demo_completed',
            user_id='demo_user_123',
            properties={
                'demo_version': '2.0.0',
                'completion_time': datetime.utcnow().isoformat(),
                'features_used': ['meal_planning', 'community', 'gamification']
            }
        )
        print("✅ Analytics event tracked")

    except Exception as e:
        print(f"❌ Analytics tracking failed: {e}")

    print("\n🎉 Demo completed successfully!")
    print("\nNext steps:")
    print("• Explore the full API documentation")
    print("• Set up webhook endpoints for real-time events")
    print("• Integrate with your application's user system")
    print("• Implement error handling and retry logic")

if __name__ == '__main__':
    main()
```

## Testing

```python
import unittest
from unittest.mock import patch, Mock
import json

class TestAIGenome_Client(unittest.TestCase):
    """Test cases for AI Nutritionist API client"""

    def setUp(self):
        self.client = AIGenome_Client(
            base_url='https://api.test.com/v1',
            api_token='test_token'
        )

    @patch('requests.Session.request')
    def test_successful_request(self, mock_request):
        """Test successful API request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        result = self.client.get('test/endpoint')

        self.assertEqual(result, {'success': True})
        mock_request.assert_called_once()

    @patch('requests.Session.request')
    def test_rate_limit_error(self, mock_request):
        """Test rate limit handling"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_request.return_value = mock_response

        with self.assertRaises(RateLimitError):
            self.client.get('test/endpoint')

    def test_meal_plan_parsing(self):
        """Test meal plan parsing from API response"""
        meal_client = MealPlanningClient(api_token='test_token')

        sample_response = {
            'plan_id': 'test_plan_123',
            'user_id': 'test_user_456',
            'week_start': '2024-10-14',
            'generated_at': '2024-10-13T15:30:00Z',
            'estimated_cost': 89.45,
            'total_calories': 8400,
            'meals': [
                {
                    'meal_id': 'meal_789',
                    'day': 'monday',
                    'meal_type': 'dinner',
                    'title': 'Test Meal',
                    'description': 'Test Description',
                    'ingredients': ['ingredient1', 'ingredient2'],
                    'calories': 520,
                    'prep_minutes': 30,
                    'macros': {'protein': 20, 'carbs': 40, 'fat': 15},
                    'cost': 8.50,
                    'tags': ['vegetarian']
                }
            ],
            'grocery_list': []
        }

        plan = meal_client._parse_meal_plan(sample_response)

        self.assertEqual(plan.plan_id, 'test_plan_123')
        self.assertEqual(len(plan.meals), 1)
        self.assertEqual(plan.meals[0].title, 'Test Meal')
        self.assertEqual(plan.estimated_cost, 89.45)

if __name__ == '__main__':
    unittest.main()
```

## Environment Setup

Create a `.env` file for configuration:

```bash
# .env file
AI_NUTRITIONIST_API_URL=https://api.ai-nutritionist.com/v1
AI_NUTRITIONIST_API_TOKEN=your_api_token_here
API_TIMEOUT=30
API_MAX_RETRIES=3
API_DEBUG=false
```

Load environment variables:

```python
from dotenv import load_dotenv
load_dotenv()

# Now you can use the configured client
client = ConfiguredClient()
```

This comprehensive Python client provides all the functionality needed to integrate with the AI Nutritionist API, including authentication, meal planning, community features, gamification, analytics, and integrations.
