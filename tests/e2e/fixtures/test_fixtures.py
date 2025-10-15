"""
E2E Test Fixtures

Provides fixtures for E2E testing including test data,
environment setup, and resource management.
"""

import asyncio
import pytest
import json
from typing import Dict, Any, List, Generator, AsyncGenerator
from datetime import datetime, timedelta

from ..framework import (
    TestUser, TestEnvironment, create_test_environment, generate_test_data
)
from ..utils.automation import (
    SeleniumAutomation, APIAutomation, MessageSimulationAutomation,
    DatabaseVerificationAutomation
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", params=["local", "staging"])
def test_environment(request) -> TestEnvironment:
    """Provide test environment configuration"""
    env_name = request.param
    return create_test_environment(env_name)


@pytest.fixture(scope="session")
async def api_automation(test_environment: TestEnvironment) -> AsyncGenerator[APIAutomation, None]:
    """Provide API automation instance"""
    api = APIAutomation(test_environment.api_base_url)
    await api.create_session()
    yield api
    await api.close_session()


@pytest.fixture(scope="function")
def selenium_automation() -> Generator[SeleniumAutomation, None, None]:
    """Provide Selenium automation instance"""
    selenium = SeleniumAutomation(browser="chrome", headless=True)
    selenium.setup_driver()
    yield selenium
    selenium.close_driver()


@pytest.fixture(scope="function")
async def message_simulation(test_environment: TestEnvironment) -> AsyncGenerator[MessageSimulationAutomation, None]:
    """Provide message simulation automation"""
    sim = MessageSimulationAutomation(test_environment.environment)
    await sim.setup(test_environment.api_base_url)
    yield sim
    await sim.cleanup()


@pytest.fixture(scope="function")
def database_verification(test_environment: TestEnvironment) -> DatabaseVerificationAutomation:
    """Provide database verification utilities"""
    db_verify = DatabaseVerificationAutomation(test_environment.environment)
    db_verify.setup_aws_clients()
    return db_verify


@pytest.fixture(scope="function")
def test_user() -> TestUser:
    """Provide a single test user"""
    return TestUser(
        user_id=f"test_user_{int(datetime.utcnow().timestamp())}",
        phone_number=f"+1555{int(datetime.utcnow().timestamp()) % 10000:04d}",
        email=f"test{int(datetime.utcnow().timestamp())}@example.com",
        name=f"Test User {int(datetime.utcnow().timestamp())}",
        dietary_preferences=["vegetarian"],
        health_goals=["weight_loss"],
        subscription_tier="free"
    )


@pytest.fixture(scope="function")
def test_users() -> List[TestUser]:
    """Provide multiple test users"""
    timestamp = int(datetime.utcnow().timestamp())
    
    users = []
    for i in range(5):
        user = TestUser(
            user_id=f"test_user_{timestamp}_{i}",
            phone_number=f"+1555{(timestamp + i) % 10000:04d}",
            email=f"test{timestamp}_{i}@example.com",
            name=f"Test User {i + 1}",
            dietary_preferences=["vegetarian", "vegan", "keto", "paleo", ""][i],
            health_goals=["weight_loss", "muscle_gain", "maintenance", "general_health", "weight_gain"][i],
            subscription_tier=["free", "premium", "enterprise", "free", "premium"][i]
        )
        users.append(user)
    
    return users


@pytest.fixture(scope="function")
def premium_test_user() -> TestUser:
    """Provide a premium test user"""
    return TestUser(
        user_id=f"premium_user_{int(datetime.utcnow().timestamp())}",
        phone_number=f"+1555{int(datetime.utcnow().timestamp()) % 10000:04d}",
        email=f"premium{int(datetime.utcnow().timestamp())}@example.com",
        name=f"Premium User {int(datetime.utcnow().timestamp())}",
        dietary_preferences=["vegetarian", "gluten_free"],
        health_goals=["weight_loss", "muscle_gain"],
        subscription_tier="premium",
        onboarding_completed=True
    )


@pytest.fixture(scope="function")
def family_test_user() -> TestUser:
    """Provide a test user with family members"""
    timestamp = int(datetime.utcnow().timestamp())
    
    family_members = [
        {
            "name": "Spouse Name",
            "age": 32,
            "relationship": "spouse",
            "dietary_preferences": ["vegetarian"],
            "health_goals": ["maintenance"]
        },
        {
            "name": "Child Name",
            "age": 8,
            "relationship": "child",
            "dietary_preferences": ["kid_friendly"],
            "health_goals": ["healthy_growth"]
        }
    ]
    
    return TestUser(
        user_id=f"family_user_{timestamp}",
        phone_number=f"+1555{timestamp % 10000:04d}",
        email=f"family{timestamp}@example.com",
        name=f"Family User {timestamp}",
        dietary_preferences=["vegetarian"],
        health_goals=["weight_loss"],
        subscription_tier="premium",
        family_members=family_members,
        onboarding_completed=True
    )


@pytest.fixture(scope="function")
def test_meal_data() -> Dict[str, Any]:
    """Provide test meal data"""
    return {
        "breakfast": {
            "name": "Oatmeal with Berries",
            "calories": 300,
            "protein": 10,
            "carbs": 45,
            "fat": 8,
            "fiber": 8,
            "ingredients": ["oats", "blueberries", "milk", "honey"]
        },
        "lunch": {
            "name": "Grilled Chicken Salad", 
            "calories": 450,
            "protein": 35,
            "carbs": 15,
            "fat": 25,
            "fiber": 6,
            "ingredients": ["chicken breast", "mixed greens", "tomatoes", "cucumber", "olive oil"]
        },
        "dinner": {
            "name": "Salmon with Quinoa",
            "calories": 520,
            "protein": 40,
            "carbs": 35,
            "fat": 22,
            "fiber": 5,
            "ingredients": ["salmon fillet", "quinoa", "broccoli", "lemon", "herbs"]
        },
        "snack": {
            "name": "Greek Yogurt with Nuts",
            "calories": 180,
            "protein": 15,
            "carbs": 12,
            "fat": 8,
            "fiber": 2,
            "ingredients": ["greek yogurt", "almonds", "walnuts"]
        }
    }


@pytest.fixture(scope="function")
def test_recipe_data() -> List[Dict[str, Any]]:
    """Provide test recipe data"""
    return [
        {
            "id": "recipe_001",
            "name": "Healthy Chicken Stir Fry",
            "description": "Quick and nutritious chicken stir fry with vegetables",
            "prep_time": 15,
            "cook_time": 10,
            "servings": 4,
            "difficulty": "easy",
            "calories_per_serving": 320,
            "ingredients": [
                {"name": "chicken breast", "amount": "1 lb", "category": "protein"},
                {"name": "bell peppers", "amount": "2 cups", "category": "vegetable"},
                {"name": "broccoli", "amount": "2 cups", "category": "vegetable"},
                {"name": "soy sauce", "amount": "3 tbsp", "category": "condiment"},
                {"name": "garlic", "amount": "3 cloves", "category": "aromatic"},
                {"name": "ginger", "amount": "1 tbsp", "category": "aromatic"},
                {"name": "olive oil", "amount": "2 tbsp", "category": "fat"}
            ],
            "instructions": [
                "Cut chicken into bite-sized pieces",
                "Heat oil in large pan or wok",
                "Cook chicken until golden brown",
                "Add vegetables and stir fry for 5 minutes",
                "Add soy sauce, garlic, and ginger",
                "Stir fry for 2 more minutes",
                "Serve hot over rice or quinoa"
            ],
            "nutrition": {
                "calories": 320,
                "protein": 35,
                "carbs": 12,
                "fat": 14,
                "fiber": 4
            },
            "tags": ["healthy", "quick", "protein", "low_carb"],
            "dietary_labels": ["gluten_free", "dairy_free"]
        },
        {
            "id": "recipe_002", 
            "name": "Vegetarian Buddha Bowl",
            "description": "Colorful and nutritious Buddha bowl with quinoa and vegetables",
            "prep_time": 20,
            "cook_time": 25,
            "servings": 2,
            "difficulty": "medium",
            "calories_per_serving": 420,
            "ingredients": [
                {"name": "quinoa", "amount": "1 cup", "category": "grain"},
                {"name": "sweet potato", "amount": "1 large", "category": "vegetable"},
                {"name": "chickpeas", "amount": "1 can", "category": "protein"},
                {"name": "spinach", "amount": "2 cups", "category": "vegetable"},
                {"name": "avocado", "amount": "1", "category": "fat"},
                {"name": "tahini", "amount": "3 tbsp", "category": "fat"},
                {"name": "lemon juice", "amount": "2 tbsp", "category": "acid"}
            ],
            "instructions": [
                "Cook quinoa according to package instructions",
                "Roast cubed sweet potato at 400°F for 25 minutes",
                "Drain and rinse chickpeas",
                "Prepare tahini dressing with lemon juice",
                "Assemble bowl with quinoa as base",
                "Top with roasted sweet potato, chickpeas, and spinach",
                "Add sliced avocado and drizzle with dressing"
            ],
            "nutrition": {
                "calories": 420,
                "protein": 18,
                "carbs": 55,
                "fat": 16,
                "fiber": 12
            },
            "tags": ["vegetarian", "vegan", "healthy", "bowl"],
            "dietary_labels": ["vegetarian", "vegan", "gluten_free"]
        }
    ]


@pytest.fixture(scope="function")
def test_subscription_data() -> Dict[str, Any]:
    """Provide test subscription data"""
    return {
        "free": {
            "tier": "free",
            "price": 0,
            "features": [
                "basic_meal_planning",
                "nutrition_tracking",
                "recipe_access_limited"
            ],
            "limits": {
                "meal_plans_per_month": 4,
                "recipes_per_day": 3,
                "family_members": 0
            }
        },
        "premium": {
            "tier": "premium",
            "price": 9.99,
            "features": [
                "unlimited_meal_planning",
                "advanced_nutrition_tracking",
                "unlimited_recipe_access",
                "family_management",
                "health_data_sync",
                "priority_support"
            ],
            "limits": {
                "meal_plans_per_month": -1,  # Unlimited
                "recipes_per_day": -1,
                "family_members": 6
            }
        },
        "enterprise": {
            "tier": "enterprise", 
            "price": 29.99,
            "features": [
                "everything_in_premium",
                "nutritionist_consultations",
                "custom_meal_plans",
                "corporate_wellness",
                "advanced_analytics",
                "white_label_options"
            ],
            "limits": {
                "meal_plans_per_month": -1,
                "recipes_per_day": -1,
                "family_members": -1
            }
        }
    }


@pytest.fixture(scope="function")
def test_health_data() -> Dict[str, Any]:
    """Provide test health data"""
    base_date = datetime.utcnow() - timedelta(days=7)
    
    return {
        "activity_data": [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "steps": 8000 + (i * 200),
                "calories_burned": 300 + (i * 25),
                "active_minutes": 45 + (i * 5),
                "distance_miles": 3.5 + (i * 0.2)
            }
            for i in range(7)
        ],
        "sleep_data": [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "duration_hours": 7.5 + (i * 0.1),
                "quality_score": 75 + (i * 2),
                "deep_sleep_hours": 2.0 + (i * 0.1),
                "rem_sleep_hours": 1.8 + (i * 0.05)
            }
            for i in range(7)
        ],
        "weight_data": [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "weight_lbs": 150.0 - (i * 0.3),
                "body_fat_percentage": 22.0 - (i * 0.1),
                "muscle_mass_lbs": 110.0 + (i * 0.1)
            }
            for i in range(7)
        ],
        "heart_rate_data": [
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "resting_hr": 65 - i,
                "max_hr": 180 + i,
                "avg_hr": 120 + (i * 2)
            }
            for i in range(7)
        ]
    }


@pytest.fixture(scope="function")
def performance_test_config() -> Dict[str, Any]:
    """Provide performance test configuration"""
    return {
        "load_test": {
            "concurrent_users": [10, 50, 100, 200],
            "duration_minutes": [5, 10, 15, 30],
            "ramp_up_time": 60
        },
        "stress_test": {
            "max_users": 1000,
            "increment_size": 100,
            "increment_duration": 300,
            "breaking_point_threshold": {
                "error_rate": 0.05,
                "response_time_p95": 5.0
            }
        },
        "spike_test": {
            "baseline_users": 10,
            "spike_users": 500,
            "spike_duration": 300,
            "recovery_time": 300
        },
        "endurance_test": {
            "duration_hours": 2,
            "sustained_users": 100,
            "monitoring_interval": 300
        }
    }


@pytest.fixture(scope="function")
async def test_data_cleanup(database_verification: DatabaseVerificationAutomation):
    """Fixture to handle test data cleanup"""
    created_user_ids = []
    
    def register_user(user_id: str):
        created_user_ids.append(user_id)
    
    yield register_user
    
    # Cleanup after test
    if created_user_ids:
        await database_verification.cleanup_test_data(created_user_ids)


@pytest.fixture(scope="function")
def mock_external_services():
    """Provide mocked external services"""
    mocks = {
        "openai": {
            "chat.completions.create": lambda **kwargs: {
                "choices": [{"message": {"content": "Mock AI response"}}]
            }
        },
        "stripe": {
            "Payment.create": lambda **kwargs: {"id": "pi_test_123", "status": "succeeded"},
            "Subscription.create": lambda **kwargs: {"id": "sub_test_123", "status": "active"}
        },
        "aws_pinpoint": {
            "send_messages": lambda **kwargs: {"MessageResponse": {"Result": {"success": True}}}
        },
        "edamam": {
            "recipe_search": lambda **kwargs: {
                "hits": [{"recipe": {"label": "Mock Recipe", "calories": 300}}]
            },
            "nutrition_analysis": lambda **kwargs: {
                "calories": 300,
                "nutrients": {"PROCNT": {"quantity": 20}}
            }
        }
    }
    
    return mocks


@pytest.fixture(scope="function")
def browser_configurations():
    """Provide different browser configurations for cross-browser testing"""
    return [
        {"browser": "chrome", "headless": True, "window_size": "1920,1080"},
        {"browser": "firefox", "headless": True, "window_size": "1920,1080"},
        {"browser": "chrome", "headless": False, "window_size": "1366,768"},  # For debugging
    ]


@pytest.fixture(scope="function")
def mobile_configurations():
    """Provide mobile device configurations for responsive testing"""
    return [
        {"device": "iPhone 12", "width": 390, "height": 844, "user_agent": "iPhone"},
        {"device": "iPad", "width": 768, "height": 1024, "user_agent": "iPad"},
        {"device": "Android Phone", "width": 360, "height": 640, "user_agent": "Android"},
        {"device": "Android Tablet", "width": 800, "height": 1280, "user_agent": "Android"}
    ]


@pytest.fixture(scope="session")
def test_report_data():
    """Collect test execution data for reporting"""
    report_data = {
        "start_time": datetime.utcnow().isoformat(),
        "test_results": [],
        "performance_metrics": [],
        "error_logs": []
    }
    
    yield report_data
    
    # Generate final report
    report_data["end_time"] = datetime.utcnow().isoformat()
    report_data["total_duration"] = (
        datetime.fromisoformat(report_data["end_time"]) - 
        datetime.fromisoformat(report_data["start_time"])
    ).total_seconds()
    
    # Save report to file
    with open(f"e2e_test_report_{int(datetime.utcnow().timestamp())}.json", "w") as f:
        json.dump(report_data, f, indent=2)
