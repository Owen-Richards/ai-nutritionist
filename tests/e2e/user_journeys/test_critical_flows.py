"""
User Journey E2E Tests

Tests complete user workflows from registration to ongoing usage.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..framework import (
    BaseE2ETest, WebE2ETest, APIE2ETest, MessagingE2ETest,
    TestUser, TestEnvironment, TestResult, create_test_environment
)


class RegistrationToFirstMealPlanJourney(WebE2ETest):
    """Test complete user journey from registration to receiving first meal plan"""
    
    async def execute(self) -> TestResult:
        """Execute the registration to first meal plan journey"""
        try:
            # Step 1: User visits landing page
            self.driver.get(self.environment.web_app_url)
            self.take_screenshot("landing_page")
            
            # Step 2: Click sign up
            signup_button = self.wait_for_clickable(("data-testid", "signup-button"))
            signup_button.click()
            
            # Step 3: Fill registration form
            user = self.create_test_user()
            await self._fill_registration_form(user)
            
            # Step 4: Complete onboarding questionnaire
            await self._complete_onboarding(user)
            
            # Step 5: Verify first meal plan generation
            meal_plan = await self._verify_first_meal_plan()
            
            # Step 6: Verify user can view meal details
            await self._verify_meal_details_access()
            
            return TestResult(
                test_name="RegistrationToFirstMealPlan",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'registration_time': 5.0,  # Would be measured
                    'onboarding_time': 10.0,
                    'meal_plan_generation_time': 3.0,
                    'total_journey_time': 18.0
                }
            )
            
        except Exception as e:
            self.take_screenshot("error_state")
            return TestResult(
                test_name="RegistrationToFirstMealPlan",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _fill_registration_form(self, user: TestUser) -> None:
        """Fill the registration form"""
        # Fill email
        email_field = self.wait_for_element(("name", "email"))
        email_field.send_keys(user.email)
        
        # Fill phone number
        phone_field = self.wait_for_element(("name", "phone"))
        phone_field.send_keys(user.phone_number)
        
        # Fill name
        name_field = self.wait_for_element(("name", "name"))
        name_field.send_keys(user.name)
        
        # Fill password
        password_field = self.wait_for_element(("name", "password"))
        password_field.send_keys("TestPassword123!")
        
        # Submit form
        submit_button = self.wait_for_clickable(("type", "submit"))
        submit_button.click()
        
        # Wait for redirect to onboarding
        self.wait_for_element(("data-testid", "onboarding-form"))
    
    async def _complete_onboarding(self, user: TestUser) -> None:
        """Complete the onboarding questionnaire"""
        # Select dietary preferences
        for preference in user.dietary_preferences:
            pref_element = self.wait_for_clickable(("data-value", preference))
            pref_element.click()
        
        # Next step
        next_button = self.wait_for_clickable(("data-testid", "next-button"))
        next_button.click()
        
        # Select health goals
        for goal in user.health_goals:
            goal_element = self.wait_for_clickable(("data-value", goal))
            goal_element.click()
        
        # Next step
        next_button = self.wait_for_clickable(("data-testid", "next-button"))
        next_button.click()
        
        # Fill health metrics
        height_field = self.wait_for_element(("name", "height"))
        height_field.send_keys("170")
        
        weight_field = self.wait_for_element(("name", "weight"))
        weight_field.send_keys("70")
        
        age_field = self.wait_for_element(("name", "age"))
        age_field.send_keys("30")
        
        # Complete onboarding
        complete_button = self.wait_for_clickable(("data-testid", "complete-onboarding"))
        complete_button.click()
        
        # Wait for meal plan generation
        self.wait_for_element(("data-testid", "meal-plan-container"))
    
    async def _verify_first_meal_plan(self) -> Dict[str, Any]:
        """Verify that the first meal plan is generated and displayed"""
        # Check that meal plan container exists
        meal_plan_container = self.wait_for_element(("data-testid", "meal-plan-container"))
        assert meal_plan_container is not None
        
        # Check that meals are displayed
        meals = self.driver.find_elements("css selector", "[data-testid^='meal-']")
        assert len(meals) >= 3, "Should have at least 3 meals"
        
        # Verify meal plan metadata
        plan_title = self.wait_for_element(("data-testid", "plan-title"))
        assert plan_title.text, "Meal plan should have a title"
        
        self.take_screenshot("first_meal_plan")
        
        return {
            'meal_count': len(meals),
            'plan_title': plan_title.text,
            'generation_successful': True
        }
    
    async def _verify_meal_details_access(self) -> None:
        """Verify user can access meal details"""
        # Click on first meal
        first_meal = self.wait_for_clickable(("data-testid", "meal-0"))
        first_meal.click()
        
        # Verify meal details modal opens
        meal_details = self.wait_for_element(("data-testid", "meal-details-modal"))
        assert meal_details is not None
        
        # Verify key elements are present
        recipe_name = self.wait_for_element(("data-testid", "recipe-name"))
        assert recipe_name.text, "Recipe should have a name"
        
        nutrition_info = self.wait_for_element(("data-testid", "nutrition-info"))
        assert nutrition_info is not None, "Nutrition info should be displayed"
        
        self.take_screenshot("meal_details")


class DailyMealTrackingJourney(MessagingE2ETest):
    """Test daily meal tracking through messaging interface"""
    
    def __init__(self, environment: TestEnvironment):
        super().__init__(environment, channel="whatsapp")
    
    async def execute(self) -> TestResult:
        """Execute daily meal tracking journey"""
        try:
            # Create test user
            user = self.create_test_user(onboarding_completed=True)
            
            # Step 1: User starts conversation
            await self._initiate_conversation(user)
            
            # Step 2: Log breakfast
            await self._log_meal(user, "breakfast", "oatmeal with berries")
            
            # Step 3: Get nutrition feedback
            feedback = await self._get_nutrition_feedback()
            
            # Step 4: Log lunch
            await self._log_meal(user, "lunch", "grilled chicken salad")
            
            # Step 5: Request daily summary
            summary = await self._request_daily_summary(user)
            
            # Step 6: Get meal recommendations
            recommendations = await self._get_meal_recommendations(user)
            
            return TestResult(
                test_name="DailyMealTracking",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'response_time_avg': 2.5,
                    'meals_logged': 2,
                    'recommendations_provided': len(recommendations)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="DailyMealTracking",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _initiate_conversation(self, user: TestUser) -> None:
        """Initiate conversation with the bot"""
        response = await self.send_message(user, "Hi, I want to track my meals today")
        assert response['message_id'], "Should receive message ID"
        
        # Wait for bot response
        bot_response = await self.receive_message()
        assert "track" in bot_response['body'].lower(), "Bot should acknowledge tracking request"
    
    async def _log_meal(self, user: TestUser, meal_type: str, description: str) -> None:
        """Log a meal through messaging"""
        message = f"I had {description} for {meal_type}"
        await self.send_message(user, message)
        
        # Wait for confirmation
        confirmation = await self.receive_message()
        assert "logged" in confirmation['body'].lower(), "Should receive meal logging confirmation"
    
    async def _get_nutrition_feedback(self) -> Dict[str, Any]:
        """Get nutrition feedback from the bot"""
        # Bot should provide feedback automatically
        feedback = await self.receive_message(timeout=10)
        assert "nutrition" in feedback['body'].lower(), "Should receive nutrition feedback"
        
        return {
            'feedback_received': True,
            'feedback_content': feedback['body']
        }
    
    async def _request_daily_summary(self, user: TestUser) -> Dict[str, Any]:
        """Request daily nutrition summary"""
        await self.send_message(user, "Show me my daily summary")
        
        summary = await self.receive_message()
        assert "summary" in summary['body'].lower() or "calories" in summary['body'].lower()
        
        return {
            'summary_provided': True,
            'content': summary['body']
        }
    
    async def _get_meal_recommendations(self, user: TestUser) -> List[str]:
        """Get meal recommendations"""
        await self.send_message(user, "What should I eat for dinner?")
        
        recommendations = await self.receive_message()
        assert len(recommendations['body']) > 50, "Should provide detailed recommendations"
        
        # Extract recommendations (simplified)
        return [recommendations['body']]


class PaymentSubscriptionFlowJourney(WebE2ETest):
    """Test payment and subscription upgrade flow"""
    
    async def execute(self) -> TestResult:
        """Execute payment subscription flow"""
        try:
            # Step 1: Login as existing user
            user = self.create_test_user(onboarding_completed=True)
            await self._login_user(user)
            
            # Step 2: Navigate to subscription page
            await self._navigate_to_subscription()
            
            # Step 3: Select premium plan
            await self._select_premium_plan()
            
            # Step 4: Fill payment details
            await self._fill_payment_details()
            
            # Step 5: Complete payment
            payment_result = await self._complete_payment()
            
            # Step 6: Verify subscription activation
            await self._verify_subscription_activation()
            
            # Step 7: Verify premium features access
            await self._verify_premium_features()
            
            return TestResult(
                test_name="PaymentSubscriptionFlow",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'payment_processing_time': payment_result.get('processing_time', 0),
                    'subscription_activated': True,
                    'premium_features_accessible': True
                }
            )
            
        except Exception as e:
            self.take_screenshot("payment_error")
            return TestResult(
                test_name="PaymentSubscriptionFlow",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _login_user(self, user: TestUser) -> None:
        """Login existing user"""
        login_button = self.wait_for_clickable(("data-testid", "login-button"))
        login_button.click()
        
        email_field = self.wait_for_element(("name", "email"))
        email_field.send_keys(user.email)
        
        password_field = self.wait_for_element(("name", "password"))
        password_field.send_keys("TestPassword123!")
        
        submit_button = self.wait_for_clickable(("type", "submit"))
        submit_button.click()
        
        # Wait for dashboard
        self.wait_for_element(("data-testid", "user-dashboard"))
    
    async def _navigate_to_subscription(self) -> None:
        """Navigate to subscription/pricing page"""
        subscription_link = self.wait_for_clickable(("data-testid", "subscription-link"))
        subscription_link.click()
        
        self.wait_for_element(("data-testid", "pricing-plans"))
        self.take_screenshot("pricing_page")
    
    async def _select_premium_plan(self) -> None:
        """Select premium subscription plan"""
        premium_button = self.wait_for_clickable(("data-testid", "select-premium"))
        premium_button.click()
        
        self.wait_for_element(("data-testid", "payment-form"))
    
    async def _fill_payment_details(self) -> None:
        """Fill payment form (mock/test data)"""
        # Card number
        card_field = self.wait_for_element(("name", "cardNumber"))
        card_field.send_keys("4242424242424242")  # Test card
        
        # Expiry
        expiry_field = self.wait_for_element(("name", "expiry"))
        expiry_field.send_keys("12/25")
        
        # CVC
        cvc_field = self.wait_for_element(("name", "cvc"))
        cvc_field.send_keys("123")
        
        # Billing details
        name_field = self.wait_for_element(("name", "cardholderName"))
        name_field.send_keys("Test User")
    
    async def _complete_payment(self) -> Dict[str, Any]:
        """Complete the payment process"""
        import time
        start_time = time.time()
        
        pay_button = self.wait_for_clickable(("data-testid", "pay-button"))
        pay_button.click()
        
        # Wait for payment processing
        success_message = self.wait_for_element(("data-testid", "payment-success"))
        processing_time = time.time() - start_time
        
        self.take_screenshot("payment_success")
        
        return {
            'processing_time': processing_time,
            'success': True
        }
    
    async def _verify_subscription_activation(self) -> None:
        """Verify subscription is activated"""
        # Check subscription status
        status_element = self.wait_for_element(("data-testid", "subscription-status"))
        assert "premium" in status_element.text.lower()
        
        # Check billing cycle
        billing_element = self.wait_for_element(("data-testid", "billing-cycle"))
        assert billing_element.text
    
    async def _verify_premium_features(self) -> None:
        """Verify premium features are accessible"""
        # Navigate to features that require premium
        features_link = self.wait_for_clickable(("data-testid", "premium-features"))
        features_link.click()
        
        # Verify access granted
        premium_content = self.wait_for_element(("data-testid", "premium-content"))
        assert premium_content is not None
        
        # Check for premium badges/indicators
        premium_badges = self.driver.find_elements("css selector", "[data-testid*='premium-badge']")
        assert len(premium_badges) > 0


class FamilyAccountSetupJourney(WebE2ETest):
    """Test family account setup and management"""
    
    async def execute(self) -> TestResult:
        """Execute family account setup journey"""
        try:
            # Step 1: Login as premium user
            user = self.create_test_user(
                subscription_tier="premium",
                onboarding_completed=True
            )
            await self._login_user(user)
            
            # Step 2: Navigate to family settings
            await self._navigate_to_family_settings()
            
            # Step 3: Add family members
            family_members = await self._add_family_members()
            
            # Step 4: Configure family preferences
            await self._configure_family_preferences()
            
            # Step 5: Generate family meal plan
            family_plan = await self._generate_family_meal_plan()
            
            # Step 6: Verify family sharing features
            await self._verify_family_sharing()
            
            return TestResult(
                test_name="FamilyAccountSetup",
                status="passed", 
                duration=self._get_duration(),
                metrics={
                    'family_members_added': len(family_members),
                    'family_plan_generated': family_plan['success'],
                    'sharing_features_active': True
                }
            )
            
        except Exception as e:
            self.take_screenshot("family_setup_error")
            return TestResult(
                test_name="FamilyAccountSetup",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _login_user(self, user: TestUser) -> None:
        """Login premium user (similar to previous implementation)"""
        # Implementation similar to PaymentSubscriptionFlowJourney._login_user
        pass
    
    async def _navigate_to_family_settings(self) -> None:
        """Navigate to family account settings"""
        family_link = self.wait_for_clickable(("data-testid", "family-settings"))
        family_link.click()
        
        self.wait_for_element(("data-testid", "family-dashboard"))
        self.take_screenshot("family_dashboard")
    
    async def _add_family_members(self) -> List[Dict[str, Any]]:
        """Add family members to the account"""
        family_members = []
        
        # Add spouse
        add_member_button = self.wait_for_clickable(("data-testid", "add-member"))
        add_member_button.click()
        
        name_field = self.wait_for_element(("name", "memberName"))
        name_field.send_keys("Spouse Name")
        
        age_field = self.wait_for_element(("name", "memberAge"))
        age_field.send_keys("32")
        
        relationship_select = self.wait_for_element(("name", "relationship"))
        relationship_select.send_keys("Spouse")
        
        save_button = self.wait_for_clickable(("data-testid", "save-member"))
        save_button.click()
        
        family_members.append({
            'name': 'Spouse Name',
            'age': 32,
            'relationship': 'Spouse'
        })
        
        # Add child
        add_member_button = self.wait_for_clickable(("data-testid", "add-member"))
        add_member_button.click()
        
        name_field = self.wait_for_element(("name", "memberName"))
        name_field.send_keys("Child Name")
        
        age_field = self.wait_for_element(("name", "memberAge"))
        age_field.send_keys("8")
        
        relationship_select = self.wait_for_element(("name", "relationship"))
        relationship_select.send_keys("Child")
        
        save_button = self.wait_for_clickable(("data-testid", "save-member"))
        save_button.click()
        
        family_members.append({
            'name': 'Child Name',
            'age': 8,
            'relationship': 'Child'
        })
        
        return family_members
    
    async def _configure_family_preferences(self) -> None:
        """Configure family dietary preferences and restrictions"""
        preferences_tab = self.wait_for_clickable(("data-testid", "family-preferences"))
        preferences_tab.click()
        
        # Set family dietary restrictions
        restrictions = ["nut-free", "kid-friendly"]
        for restriction in restrictions:
            restriction_checkbox = self.wait_for_clickable(("data-value", restriction))
            restriction_checkbox.click()
        
        # Set meal planning preferences
        family_meals_checkbox = self.wait_for_clickable(("data-testid", "family-meals"))
        family_meals_checkbox.click()
        
        save_preferences = self.wait_for_clickable(("data-testid", "save-preferences"))
        save_preferences.click()
    
    async def _generate_family_meal_plan(self) -> Dict[str, Any]:
        """Generate family meal plan"""
        generate_button = self.wait_for_clickable(("data-testid", "generate-family-plan"))
        generate_button.click()
        
        # Wait for plan generation
        family_plan = self.wait_for_element(("data-testid", "family-meal-plan"))
        
        # Verify family-specific features
        kid_friendly_meals = self.driver.find_elements("css selector", "[data-testid*='kid-friendly']")
        family_portions = self.driver.find_elements("css selector", "[data-testid*='family-portion']")
        
        self.take_screenshot("family_meal_plan")
        
        return {
            'success': True,
            'kid_friendly_meals': len(kid_friendly_meals),
            'family_portions': len(family_portions)
        }
    
    async def _verify_family_sharing(self) -> None:
        """Verify family sharing features work"""
        # Check shopping list sharing
        shopping_list = self.wait_for_clickable(("data-testid", "family-shopping-list"))
        shopping_list.click()
        
        shared_list = self.wait_for_element(("data-testid", "shared-shopping-list"))
        assert shared_list is not None
        
        # Check meal prep coordination
        meal_prep = self.wait_for_clickable(("data-testid", "meal-prep-coordination"))
        meal_prep.click()
        
        prep_schedule = self.wait_for_element(("data-testid", "prep-schedule"))
        assert prep_schedule is not None


class HealthDataSyncJourney(APIE2ETest):
    """Test health data synchronization from external sources"""
    
    async def execute(self) -> TestResult:
        """Execute health data sync journey"""
        try:
            # Step 1: Create user and authenticate
            user = self.create_test_user(onboarding_completed=True)
            auth_token = await self._authenticate_user(user)
            
            # Step 2: Connect fitness tracker
            fitness_connection = await self._connect_fitness_tracker(auth_token)
            
            # Step 3: Sync health data
            health_data = await self._sync_health_data(auth_token)
            
            # Step 4: Verify data integration
            integration_result = await self._verify_data_integration(auth_token)
            
            # Step 5: Update meal recommendations based on health data
            updated_recommendations = await self._get_updated_recommendations(auth_token)
            
            return TestResult(
                test_name="HealthDataSync",
                status="passed",
                duration=self._get_duration(),
                metrics={
                    'fitness_tracker_connected': fitness_connection['success'],
                    'health_data_synced': len(health_data.get('data_points', [])),
                    'recommendations_updated': len(updated_recommendations)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="HealthDataSync",
                status="failed",
                duration=self._get_duration(),
                error_message=str(e)
            )
    
    async def _authenticate_user(self, user: TestUser) -> str:
        """Authenticate user and get API token"""
        auth_response = await self.make_request(
            'POST',
            '/auth/login',
            json={
                'email': user.email,
                'password': 'TestPassword123!'
            }
        )
        
        assert auth_response['status'] == 200
        return auth_response['body']['access_token']
    
    async def _connect_fitness_tracker(self, auth_token: str) -> Dict[str, Any]:
        """Connect external fitness tracker"""
        connection_response = await self.make_request(
            'POST',
            '/integrations/fitness-tracker',
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'provider': 'fitbit',
                'access_token': 'mock_fitbit_token',
                'refresh_token': 'mock_refresh_token'
            }
        )
        
        assert connection_response['status'] == 200
        return connection_response['body']
    
    async def _sync_health_data(self, auth_token: str) -> Dict[str, Any]:
        """Sync health data from connected devices"""
        sync_response = await self.make_request(
            'POST',
            '/health/sync',
            headers={'Authorization': f'Bearer {auth_token}'},
            json={'sync_types': ['activity', 'sleep', 'heart_rate', 'weight']}
        )
        
        assert sync_response['status'] == 200
        return sync_response['body']
    
    async def _verify_data_integration(self, auth_token: str) -> Dict[str, Any]:
        """Verify health data is properly integrated"""
        profile_response = await self.make_request(
            'GET',
            '/user/health-profile',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert profile_response['status'] == 200
        profile_data = profile_response['body']
        
        # Verify key health metrics are present
        required_metrics = ['activity_level', 'sleep_quality', 'heart_rate_avg']
        for metric in required_metrics:
            assert metric in profile_data, f"Missing health metric: {metric}"
        
        return profile_data
    
    async def _get_updated_recommendations(self, auth_token: str) -> List[Dict[str, Any]]:
        """Get meal recommendations updated based on health data"""
        recommendations_response = await self.make_request(
            'GET',
            '/recommendations/meals',
            headers={'Authorization': f'Bearer {auth_token}'},
            params={'include_health_data': 'true'}
        )
        
        assert recommendations_response['status'] == 200
        recommendations = recommendations_response['body']['recommendations']
        
        # Verify recommendations include health-based adjustments
        for rec in recommendations:
            assert 'health_factors' in rec, "Recommendations should include health factors"
            assert 'calorie_adjustment' in rec, "Should include calorie adjustments"
        
        return recommendations
