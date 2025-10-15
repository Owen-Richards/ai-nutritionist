"""Simple test to verify fixture system works independently"""

import sys
from pathlib import Path

# Add the project root and tests to path
project_root = Path(__file__).parent.parent
tests_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tests_dir))

import pytest
from datetime import datetime, date
from uuid import uuid4


def test_fixture_system_basic():
    """Basic test that our fixture system loads without errors"""
    
    # Test that we can import fixtures without dependency issues
    from fixtures.user_fixtures import UserFactory, UserProfileBuilder
    from fixtures.nutrition_fixtures import RecipeFactory, MealPlanFactory
    from fixtures.health_fixtures import HealthMetricsFactory, ExerciseDataFactory
    from fixtures.payment_fixtures import SubscriptionFactory, PaymentMethodFactory
    from fixtures.mock_services import MockTwilioService, MockStripeService
    
    # Test basic factory methods work
    user_factory = UserFactory()
    user = user_factory.base_user()
    assert user.phone_number == "+1234567890"
    
    # Test recipe factory
    recipe_factory = RecipeFactory()
    recipe = recipe_factory.breakfast_recipe()
    assert recipe.name == "Berry Oatmeal"
    
    # Test health metrics
    health_factory = HealthMetricsFactory()
    metrics = health_factory.create_basic_metrics()
    assert 'user_id' in metrics
    assert 'weight_lbs' in metrics
    
    # Test subscription factory
    sub_factory = SubscriptionFactory()
    subscription = sub_factory.active_premium()
    assert subscription.tier == "premium"
    assert subscription.status == "active"
    
    # Test mock services
    mock_twilio = MockTwilioService()
    result = mock_twilio.send_sms("+1234567890", "Test message")
    assert result['success'] is True
    
    mock_stripe = MockStripeService()
    customer = mock_stripe.create_customer("test@example.com")
    assert customer['id'].startswith('cus_')


def test_user_builder_pattern():
    """Test user builder pattern works"""
    from fixtures.user_fixtures import UserProfileBuilder
    
    builder = UserProfileBuilder()
    user = (builder
            .with_phone("+1555123456")
            .with_usage_stats(meal_plans=5, consultations=3)
            .build())
    
    assert user.phone_number == "+1555123456"
    assert user.meal_plans_this_month == 5
    assert user.ai_consultations_today == 3


def test_meal_plan_generation():
    """Test meal plan fixtures work"""
    from fixtures.nutrition_fixtures import MealPlanFactory
    
    factory = MealPlanFactory()
    meal_plan = factory.create(
        user_id=str(uuid4()),
        plan_name="Test Plan",
        duration_days=7
    )
    
    assert meal_plan.name == "Test Plan"
    assert len(meal_plan.days) == 7
    assert meal_plan.household_size == 2


def test_mock_integrations():
    """Test mock service integrations work"""
    from fixtures.mock_services import MockTwilioService, MockStripeService, MockEdamamAPI
    
    # Test Twilio mock
    twilio = MockTwilioService()
    sms_result = twilio.send_sms("+1234567890", "Hello World")
    assert sms_result['success'] is True
    assert len(twilio.sent_messages) == 1
    
    # Test Stripe mock
    stripe = MockStripeService()
    customer = stripe.create_customer("user@example.com")
    payment_method = stripe.create_payment_method('card')
    subscription = stripe.create_subscription(
        customer['id'], 
        'price_premium', 
        payment_method['id']
    )
    
    assert subscription['status'] == 'active'
    assert subscription['customer'] == customer['id']
    
    # Test Edamam mock
    edamam = MockEdamamAPI()
    recipes = edamam.search_recipes("chicken", max_results=3)
    assert 'hits' in recipes
    assert len(recipes['hits']) <= 3


def test_health_data_progression():
    """Test health data progression generation"""
    from fixtures.health_fixtures import HealthMetricsFactory
    
    factory = HealthMetricsFactory()
    user_id = str(uuid4())
    
    # Test weight loss progression
    progression = factory.weight_loss_progression(
        user_id=user_id,
        start_weight=180.0,
        target_weight=160.0,
        weeks=8
    )
    
    assert len(progression) == 9  # 8 weeks + initial
    assert progression[0]['weight_lbs'] > progression[-1]['weight_lbs']
    assert all(entry['user_id'] == user_id for entry in progression)


if __name__ == "__main__":
    # Run basic tests
    test_fixture_system_basic()
    test_user_builder_pattern() 
    test_meal_plan_generation()
    test_mock_integrations()
    test_health_data_progression()
    print("✅ All fixture tests passed!")
