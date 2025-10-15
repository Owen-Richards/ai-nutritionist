"""Comprehensive test demonstrating all fixtures working together"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4

from src.config.constants import SubscriptionTier, DietaryRestriction, GoalType
from src.models.monetization import SubscriptionStatus, BillingInterval


class TestFixtureSystem:
    """Test the complete fixture system integration"""
    
    def test_user_fixtures_basic(self, create_test_user, create_premium_user, create_family_account):
        """Test basic user fixtures"""
        # Test basic user
        basic_user = create_test_user
        assert basic_user.phone_number == "+1234567890"
        assert basic_user.subscription_tier == SubscriptionTier.FREE
        assert basic_user.onboarding_completed is True
        
        # Test premium user
        premium_user = create_premium_user
        assert premium_user.subscription_tier == SubscriptionTier.PREMIUM
        assert premium_user.meal_plans_this_month > 0
        
        # Test family account
        family_user = create_family_account
        assert family_user.subscription_tier == SubscriptionTier.FAMILY
        assert family_user.preferences.household_size == 4
        assert len(family_user.goals) > 0
    
    def test_user_factory_and_builder(self, user_factory, user_profile_builder):
        """Test user factory and builder patterns"""
        # Test factory methods
        weight_loss_user = user_factory.weight_loss_user()
        assert any(goal.goal_type == GoalType.WEIGHT_LOSS for goal in weight_loss_user.goals)
        
        diabetic_user = user_factory.diabetic_user()
        assert len(diabetic_user.medical_cautions) > 0
        assert DietaryRestriction.DIABETIC_FRIENDLY in diabetic_user.preferences.dietary_restrictions
        
        # Test builder pattern
        custom_user = (user_profile_builder
                      .with_phone("+1555123456")
                      .with_subscription(SubscriptionTier.PREMIUM)
                      .with_dietary_restrictions([DietaryRestriction.VEGETARIAN])
                      .with_wearable("fitbit", "device_123")
                      .with_usage_stats(meal_plans=10, consultations=5)
                      .build())
        
        assert custom_user.phone_number == "+1555123456"
        assert custom_user.subscription_tier == SubscriptionTier.PREMIUM
        assert DietaryRestriction.VEGETARIAN in custom_user.preferences.dietary_restrictions
        assert "fitbit" in custom_user.wearable_integrations
        assert custom_user.meal_plans_this_month == 10
    
    def test_nutrition_fixtures(self, create_meal_plan, create_nutrition_goals, create_food_items):
        """Test nutrition-related fixtures"""
        # Test meal plan
        meal_plan = create_meal_plan
        assert meal_plan.plan_id is not None
        assert len(meal_plan.days) == 7  # Default weekly plan
        assert meal_plan.total_budget > 0
        
        # Test nutrition goals
        nutrition_goals = create_nutrition_goals
        assert nutrition_goals.daily_calories > 0
        assert nutrition_goals.protein_grams > 0
        
        # Test food items
        food_items = create_food_items
        assert 'proteins' in food_items
        assert 'vegetables' in food_items
        assert 'grains' in food_items
        assert len(food_items['proteins']) > 0
    
    def test_recipe_and_meal_plan_factories(self, recipe_factory, meal_plan_factory):
        """Test recipe and meal plan factories"""
        # Test recipe factory
        breakfast_recipe = recipe_factory.breakfast_recipe()
        assert "breakfast" in breakfast_recipe.meal_types
        assert breakfast_recipe.prep_time_minutes > 0
        
        dinner_recipe = recipe_factory.dinner_recipe()
        assert "dinner" in dinner_recipe.meal_types
        assert len(dinner_recipe.ingredients) > 0
        
        # Test meal plan factory
        vegetarian_plan = meal_plan_factory.vegetarian_plan()
        assert "vegetarian" in vegetarian_plan.dietary_restrictions
        
        weight_loss_plan = meal_plan_factory.weight_loss_plan()
        assert all(day.daily_calories_target <= 1500 for day in weight_loss_plan.days)
    
    def test_health_fixtures(self, create_health_metrics, create_exercise_data, create_wearable_sync_data):
        """Test health data fixtures"""
        # Test health metrics
        health_metrics = create_health_metrics
        assert 'user_id' in health_metrics
        assert 'weight_lbs' in health_metrics
        assert 'date' in health_metrics
        
        # Test exercise data
        exercise_data = create_exercise_data
        assert 'workout_id' in exercise_data
        assert 'duration_minutes' in exercise_data
        assert 'calories_burned' in exercise_data
        
        # Test wearable sync data
        wearable_data = create_wearable_sync_data
        assert 'device_type' in wearable_data
        assert 'sync_timestamp' in wearable_data
        assert 'data_points_synced' in wearable_data
    
    def test_health_factories(self, health_metrics_factory, exercise_factory, wearable_factory):
        """Test health data factories"""
        # Test weight loss progression
        user_id = str(uuid4())
        weight_loss_data = health_metrics_factory.weight_loss_progression(
            user_id=user_id, 
            start_weight=180.0, 
            target_weight=160.0, 
            weeks=12
        )
        assert len(weight_loss_data) == 13  # 12 weeks + initial
        assert weight_loss_data[0]['weight_lbs'] > weight_loss_data[-1]['weight_lbs']
        
        # Test diabetic monitoring
        diabetic_data = health_metrics_factory.diabetic_monitoring(user_id=user_id, days=7)
        assert len(diabetic_data) > 7  # Multiple readings per day
        assert all('blood_glucose_mg_dl' in reading for reading in diabetic_data)
        
        # Test weekly activity summary
        activity_summary = exercise_factory.weekly_activity_summary(user_id=user_id)
        assert 'total_workouts' in activity_summary
        assert 'total_calories_burned' in activity_summary
        assert len(activity_summary['workouts']) >= 3
        
        # Test wearable integrations
        fitbit_integration = wearable_factory.create_fitbit_integration(user_id=user_id)
        assert fitbit_integration.device_type == "fitbit"
        assert "steps" in fitbit_integration.permissions_granted
    
    def test_payment_fixtures(self, create_subscription, create_payment_method, create_invoice):
        """Test payment and subscription fixtures"""
        # Test subscription
        subscription = create_subscription
        assert subscription.tier == SubscriptionTier.PREMIUM
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.price_cents > 0
        
        # Test payment method
        payment_method = create_payment_method
        assert payment_method.type == "card"
        assert payment_method.card_last_four is not None
        assert payment_method.is_default is True
        
        # Test invoice
        invoice = create_invoice
        assert invoice.amount_cents > 0
        assert invoice.currency == "USD"
        assert invoice.paid_at is not None
    
    def test_payment_factories(self, subscription_factory, payment_method_factory, invoice_factory):
        """Test payment factories"""
        user_id = uuid4()
        
        # Test subscription scenarios
        trialing_subscription = subscription_factory.trialing_subscription(user_id)
        assert trialing_subscription.status == SubscriptionStatus.TRIALING
        assert trialing_subscription.trial_end > datetime.now()
        
        family_subscription = subscription_factory.family_subscription(user_id)
        assert family_subscription.tier == SubscriptionTier.FAMILY
        assert family_subscription.billing_interval == BillingInterval.YEARLY
        
        # Test payment methods
        visa_card = payment_method_factory.create_credit_card(user_id, "4242", "visa")
        assert visa_card.card_brand == "visa"
        assert visa_card.card_last_four == "4242"
        
        paypal_method = payment_method_factory.create_paypal(user_id)
        assert paypal_method.type == "paypal"
        assert paypal_method.paypal_email is not None
        
        # Test invoices
        failed_invoice = invoice_factory.failed_invoice(user_id)
        assert failed_invoice.paid_at is None
        assert failed_invoice.last_payment_attempt is not None
    
    def test_mock_services(self, mock_twilio, mock_stripe, mock_edamam, mock_aws_services):
        """Test mock external services"""
        # Test Twilio mock
        sms_result = mock_twilio.send_sms("+1234567890", "Test message")
        assert sms_result['success'] is True
        assert len(mock_twilio.sent_messages) == 1
        
        # Test Stripe mock
        customer = mock_stripe.create_customer("test@example.com")
        assert customer['id'].startswith('cus_')
        
        payment_method = mock_stripe.create_payment_method('card')
        assert payment_method['id'].startswith('pm_')
        
        # Test Edamam mock
        recipes = mock_edamam.search_recipes("chicken", max_results=3)
        assert 'hits' in recipes
        assert len(recipes['hits']) <= 3
        
        # Test AWS mocks
        dynamodb = mock_aws_services.create_dynamodb_mock()
        put_result = dynamodb.put_item(
            TableName='test-table',
            Item={'user_id': 'test-user', 'data': 'test-data'}
        )
        assert put_result['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_complete_user_workflow(self, user_factory, meal_plan_factory, subscription_factory, 
                                   health_metrics_factory, mock_twilio):
        """Test complete user workflow using multiple fixtures"""
        # Create a premium user
        user = user_factory.premium_user("+1555987654")
        
        # Create subscription for the user
        subscription = subscription_factory.active_premium(user.user_id)
        
        # Create a meal plan for the user
        meal_plan = meal_plan_factory.create(user_id=user.user_id)
        
        # Generate health metrics
        health_metrics = health_metrics_factory.create_basic_metrics(user.user_id)
        
        # Send notification via mocked Twilio
        notification_result = mock_twilio.send_sms(
            user.phone_number, 
            f"Your meal plan '{meal_plan.name}' is ready!"
        )
        
        # Verify the complete workflow
        assert user.subscription_tier == SubscriptionTier.PREMIUM
        assert subscription.tier == SubscriptionTier.PREMIUM
        assert meal_plan.user_id == user.user_id
        assert health_metrics['user_id'] == user.user_id
        assert notification_result['success'] is True
        assert len(mock_twilio.sent_messages) == 1
    
    def test_fixture_collections(self, users_collection, meal_plans_collection, 
                                subscription_scenarios, nutrition_goals_collection):
        """Test fixture collections"""
        # Test users collection
        assert 'basic' in users_collection
        assert 'premium' in users_collection
        assert 'family' in users_collection
        
        # Test meal plans collection
        assert 'standard' in meal_plans_collection
        assert 'vegetarian' in meal_plans_collection
        assert 'weight_loss' in meal_plans_collection
        
        # Test subscription scenarios
        assert 'active_premium' in subscription_scenarios
        assert 'trialing' in subscription_scenarios
        assert 'canceled' in subscription_scenarios
        
        # Test nutrition goals collection
        assert 'weight_loss' in nutrition_goals_collection
        assert 'muscle_gain' in nutrition_goals_collection
        assert 'maintenance' in nutrition_goals_collection
    
    def test_isolated_environment(self, isolated_test_environment):
        """Test completely isolated test environment"""
        env = isolated_test_environment
        
        # All services should be mocked
        assert 'twilio' in env
        assert 'stripe' in env
        assert 'aws' in env
        assert 'edamam' in env
        
        # Test that services work independently
        twilio = env['twilio']
        stripe = env['stripe']
        
        sms_result = twilio.send_sms("+1234567890", "Isolated test")
        customer = stripe.create_customer("isolated@test.com")
        
        assert sms_result['success'] is True
        assert customer['id'].startswith('cus_')
        
        # Verify isolation - no cross-contamination
        assert len(twilio.sent_messages) == 1
        assert len(stripe.customers) == 1
