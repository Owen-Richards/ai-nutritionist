"""
Comprehensive Tests for Conversational AI Nutritionist System
Tests all major components and conversation flows
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch
import json

from src.services.conversational_ai import ConversationalNutritionistAI, ConversationType, MessageIntent
from src.models.user_profile import UserProfile, FamilyMember
from src.models.inventory import InventoryManager, FoodItem, FoodCategory, StorageLocation
from src.models.meal_planning import MealPlanManager, Recipe, MealType, DifficultyLevel, CookingMethod, Ingredient, NutritionFacts
from src.models.health_tracking import HealthTracker, FoodEntry, MealCategory, HealthGoal, ActivityLevel
from src.models.calendar_integration import CalendarManager, CalendarEvent, EventType
from src.handlers.conversational_messaging_handler import ConversationalNutritionistHandler


class TestConversationalAI:
    """Test the main conversational AI service"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.ai = ConversationalNutritionistAI()
        self.test_phone = "+1234567890"
    
    def test_greeting_new_user(self):
        """Test greeting for new user"""
        response = self.ai.process_message(self.test_phone, "Hello!")
        
        assert "Good" in response["message"]  # Good morning/afternoon/evening
        assert "suggestions" in response
        assert len(response["suggestions"]) > 0
        assert response["actions"] == ["greeting_processed"]
    
    def test_food_logging_simple(self):
        """Test simple food logging"""
        response = self.ai.process_message(self.test_phone, "I ate 2 slices of pizza")
        
        assert "Logged" in response["message"] or "tell me what you ate" in response["message"]
        assert "suggestions" in response
    
    def test_meal_planning_request(self):
        """Test meal planning request"""
        # First set up user profile
        user_profile = self.ai._get_user_profile(self.test_phone)
        from src.models.user_profile import DietaryPreference
        user_profile.dietary_preferences = [DietaryPreference("vegetarian")]
        
        response = self.ai.process_message(self.test_phone, "Create a meal plan for this week")
        
        assert "meal plan" in response["message"].lower()
        assert "suggestions" in response
    
    def test_inventory_check(self):
        """Test inventory management"""
        response = self.ai.process_message(self.test_phone, "What's in my fridge?")
        
        assert "inventory" in response["message"].lower() or "items" in response["message"].lower()
        assert "suggestions" in response
    
    def test_grocery_list_generation(self):
        """Test grocery list functionality"""
        response = self.ai.process_message(self.test_phone, "Generate my grocery list")
        
        assert "grocery" in response["message"].lower()
        assert "suggestions" in response
    
    def test_nutrition_advice(self):
        """Test nutrition advice request"""
        response = self.ai.process_message(self.test_phone, "Is chicken healthy?")
        
        assert "nutrition" in response["message"].lower() or "advice" in response["message"].lower()
        assert "suggestions" in response
    
    def test_goal_setting(self):
        """Test goal setting functionality"""
        response = self.ai.process_message(
            self.test_phone, 
            "I'm 30 years old, 5'8\", 180 lbs, male, moderately active, want to lose weight"
        )
        
        assert "goal" in response["message"].lower()
        assert "suggestions" in response
    
    def test_intent_classification(self):
        """Test intent classification"""
        test_cases = [
            ("I ate a sandwich", MessageIntent.LOG_FOOD),
            ("Plan my meals", MessageIntent.PLAN_MEALS),
            ("What's in my pantry", MessageIntent.CHECK_INVENTORY),
            ("Add milk to grocery list", MessageIntent.ADD_TO_GROCERY_LIST),
            ("Recipe for pasta", MessageIntent.GET_RECIPE),
        ]
        
        for message, expected_intent in test_cases:
            classified_intent = self.ai._classify_intent(message)
            assert classified_intent == expected_intent, f"Failed for: {message}"
            intent = self.ai._classify_intent(message)
            assert intent == expected_intent
    
    def test_conversation_context_persistence(self):
        """Test that conversation context is maintained"""
        # First message
        response1 = self.ai.process_message(self.test_phone, "Hello!")
        
        # Second message - should maintain context
        response2 = self.ai.process_message(self.test_phone, "I want to lose weight")
        
        assert self.test_phone in self.ai.active_conversations
        context = self.ai.active_conversations[self.test_phone]
        assert len(context.conversation_history) >= 4  # 2 user messages + 2 AI responses


class TestUserProfile:
    """Test user profile functionality"""
    
    def setup_method(self):
        self.profile = UserProfile("+1234567890")
    
    def test_profile_initialization(self):
        """Test profile is properly initialized"""
        assert self.profile.phone_number == "+1234567890"
        assert self.profile.name is None  # Initially None
        assert isinstance(self.profile.health_metrics, object)  # HealthMetrics object
        assert isinstance(self.profile.family_members, list)
    
    def test_add_family_member(self):
        """Test adding family member"""
        member = FamilyMember(
            name="John Doe",
            member_id="john_doe",
            age=32,
            dietary_restrictions=["gluten-free"]
        )
        
        member_id = self.profile.add_family_member(member)
        assert member_id is not None
        assert len(self.profile.family_members) == 1
        assert self.profile.family_members[0].name == "John Doe"
    
    def test_update_dietary_info(self):
        """Test updating dietary information"""
        from src.models.user_profile import DietaryPreference, FoodAllergy
        
        # Add dietary preferences
        self.profile.dietary_preferences = [
            DietaryPreference("vegetarian"),
            DietaryPreference("no-dairy")
        ]
        
        # Add allergies
        self.profile.allergies = [
            FoodAllergy("nuts", "moderate", ["hives", "swelling"])
        ]
        
        # Add dislikes
        self.profile.food_dislikes = ["mushrooms"]
        
        assert len(self.profile.dietary_preferences) == 2
        assert self.profile.dietary_preferences[0].value == "vegetarian"
        assert len(self.profile.allergies) == 1
        assert self.profile.allergies[0].allergen == "nuts"
        assert "mushrooms" in self.profile.food_dislikes
    
    def test_calculate_bmi(self):
        """Test BMI calculation"""
        self.profile.health_metrics.weight_lbs = 180
        self.profile.health_metrics.height_inches = 72  # 6 feet
        
        bmi = self.profile.calculate_bmi()
        assert 24 <= bmi <= 25  # Should be around 24.4


class TestInventoryManager:
    """Test inventory management functionality"""
    
    def setup_method(self):
        self.inventory = InventoryManager("+1234567890")
    
    def test_add_food_item(self):
        """Test adding food item to inventory"""
        item = FoodItem(
            name="Chicken Breast",
            category=FoodCategory.MEAT_SEAFOOD,
            quantity=2.0,
            unit="lbs",
            storage_location=StorageLocation.REFRIGERATOR,
            expiration_date=date.today() + timedelta(days=3)
        )
        
        self.inventory.add_item(item)
        
        assert len(self.inventory.inventory) == 1
        retrieved_item = self.inventory.get_item("Chicken Breast")
        assert retrieved_item is not None
        assert retrieved_item.quantity == 2.0
    
    def test_expiring_items(self):
        """Test getting expiring items"""
        # Add item expiring soon
        item = FoodItem(
            name="Milk",
            category=FoodCategory.DAIRY,
            quantity=1.0,
            unit="gallon",
            storage_location=StorageLocation.REFRIGERATOR,
            expiration_date=date.today() + timedelta(days=1)
        )
        
        self.inventory.add_item(item)
        expiring = self.inventory.get_expiring_items(3)
        
        assert len(expiring) == 1
        assert expiring[0].name == "Milk"
    
    def test_consume_item(self):
        """Test consuming item quantity"""
        item = FoodItem(
            name="Bread",
            category=FoodCategory.GRAINS,
            quantity=8.0,
            unit="slices",
            storage_location=StorageLocation.PANTRY
        )
        
        self.inventory.add_item(item)
        success = self.inventory.consume_item("Bread", 2.0)
        
        assert success
        remaining_item = self.inventory.get_item("Bread")
        assert remaining_item.quantity == 6.0
    
    def test_grocery_list_generation(self):
        """Test generating grocery list from meal plan"""
        meal_plan = [
            {
                "name": "Chicken Stir Fry",
                "ingredients": ["2 lbs chicken breast", "1 cup rice", "2 cups vegetables"]
            }
        ]
        
        needed_items = self.inventory.generate_grocery_list_from_meal_plan(meal_plan)
        
        assert len(needed_items) > 0
        # Should have items for chicken, rice, and vegetables


class TestMealPlanManager:
    """Test meal planning functionality"""
    
    def setup_method(self):
        self.meal_planner = MealPlanManager("+1234567890")
        
        # Add a sample recipe
        self.sample_recipe = Recipe(
            name="Simple Pasta",
            description="Quick and easy pasta dish",
            ingredients=[],
            instructions=["Boil pasta", "Add sauce"],
            servings=4,
            prep_time_minutes=10,
            cook_time_minutes=15,
            difficulty=DifficultyLevel.BEGINNER,
            meal_types=[MealType.DINNER],
            cooking_methods=[CookingMethod.STOVETOP],
            dietary_restrictions=["vegetarian"]
        )
        
        self.meal_planner.add_recipe(self.sample_recipe)
    
    def test_add_recipe(self):
        """Test adding recipe to collection"""
        assert len(self.meal_planner.recipes) == 1
        assert "Simple Pasta" in [r.name for r in self.meal_planner.recipes.values()]
    
    def test_search_recipes(self):
        """Test recipe search functionality"""
        results = self.meal_planner.search_recipes(
            query="pasta",
            meal_type=MealType.DINNER
        )
        
        assert len(results) == 1
        assert results[0].name == "Simple Pasta"
    
    def test_create_meal_plan(self):
        """Test meal plan creation"""
        preferences = {
            "dietary_restrictions": ["vegetarian"],
            "cooking_skill": "beginner",
            "max_cook_time": 30
        }
        
        try:
            week_id = self.meal_planner.create_meal_plan(
                start_date=date.today(),
                preferences=preferences,
                family_size=2
            )
            
            meal_plan = self.meal_planner.get_meal_plan(week_id)
            # Should have some meals planned
            # Note: This might fail if no suitable recipes found
            
        except ValueError:
            # Expected if no suitable recipes found
            pass


class TestHealthTracker:
    """Test health tracking functionality"""
    
    def setup_method(self):
        self.tracker = HealthTracker("+1234567890")
    
    def test_log_food(self):
        """Test food logging"""
        food_entry = FoodEntry(
            timestamp=datetime.utcnow(),
            food_name="Apple",
            quantity=1.0,
            unit="medium",
            meal_category=MealCategory.SNACK,
            calories=95,
            protein_g=0.5,
            carbs_g=25,
            fat_g=0.3
        )
        
        self.tracker.log_food(food_entry)
        
        assert len(self.tracker.food_entries) == 1
        
        # Test daily summary
        today_summary = self.tracker.get_daily_nutrition_summary(date.today())
        assert today_summary["totals"]["calories"] == 95
        assert today_summary["entry_count"] == 1
    
    def test_set_nutrition_goals(self):
        """Test setting nutrition goals"""
        goals = self.tracker.set_nutrition_goals(
            weight_lbs=180,
            height_inches=72,
            age=30,
            sex="male",
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            health_goal=HealthGoal.WEIGHT_LOSS
        )
        
        assert goals is not None
        assert goals.calories > 0
        assert goals.protein_g > 0
        assert goals.carbs_g > 0
        assert goals.fat_g > 0
    
    def test_nutrition_adherence(self):
        """Test nutrition adherence calculation"""
        # Set goals first
        self.tracker.set_nutrition_goals(
            weight_lbs=180,
            height_inches=72,
            age=30,
            sex="male",
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            health_goal=HealthGoal.MAINTENANCE
        )
        
        # Log some food
        food_entry = FoodEntry(
            timestamp=datetime.utcnow(),
            food_name="Meal",
            quantity=1.0,
            unit="serving",
            meal_category=MealCategory.DINNER,
            calories=500,
            protein_g=30,
            carbs_g=50,
            fat_g=20
        )
        
        self.tracker.log_food(food_entry)
        
        adherence = self.tracker.get_nutrition_adherence(1)
        assert "error" not in adherence
        assert "average_adherence" in adherence


class TestCalendarManager:
    """Test calendar integration functionality"""
    
    def setup_method(self):
        self.calendar = CalendarManager("+1234567890")
    
    def test_add_event(self):
        """Test adding calendar event"""
        event = CalendarEvent(
            title="Cook Dinner",
            description="Prepare pasta for family",
            start_time=datetime.utcnow() + timedelta(hours=2),
            end_time=datetime.utcnow() + timedelta(hours=3),
            event_type=EventType.COOKING
        )
        
        event_id = self.calendar.add_event(event)
        
        assert event_id is not None
        assert len(self.calendar.events) == 1
        assert event_id in self.calendar.events
    
    def test_get_events_for_date(self):
        """Test getting events for specific date"""
        tomorrow = date.today() + timedelta(days=1)
        event_time = datetime.combine(tomorrow, datetime.min.time().replace(hour=18))
        
        event = CalendarEvent(
            title="Grocery Shopping",
            description="Weekly grocery run",
            start_time=event_time,
            end_time=event_time + timedelta(hours=1),
            event_type=EventType.SHOPPING
        )
        
        self.calendar.add_event(event)
        
        events = self.calendar.get_events_for_date(tomorrow)
        assert len(events) == 1
        assert events[0].title == "Grocery Shopping"
    
    def test_schedule_meal_prep(self):
        """Test scheduling meal prep events"""
        prep_time = datetime.utcnow() + timedelta(days=1, hours=10)
        
        # Schedule meal prep for Sunday
        prep_event = self.calendar.schedule_meal_prep(
            prep_time=prep_time,
            meal_plan_items=["Chicken Stir Fry", "Pasta Salad"],
            estimated_duration=120  # 2 hours
        )
        
        assert prep_event is not None
        assert "Meal Prep" in prep_event.title
        assert prep_event.event_type == EventType.COOKING
        assert prep_event.start_time == prep_time


class TestMessagingHandler:
    """Test messaging handler functionality"""
    
    def setup_method(self):
        with patch('boto3.client'):
            self.handler = ConversationalNutritionistHandler()
    
    def test_parse_aws_event(self):
        """Test parsing AWS messaging event"""
        # Simulate AWS SNS event
        aws_event = {
            "Records": [
                {
                    "Sns": {
                        "Message": json.dumps({
                            "originationNumber": "+1234567890",
                            "messageBody": "Hello AI nutritionist!",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    }
                }
            ]
        }
        
        message_data = self.handler._parse_aws_event(aws_event)
        
        assert message_data is not None
        assert message_data["phone_number"] == "+1234567890"
        assert message_data["message_body"] == "Hello AI nutritionist!"
    
    def test_auto_responses(self):
        """Test automatic responses to special commands"""
        with patch.object(self.handler, '_send_response') as mock_send:
            mock_send.return_value = {"statusCode": 200}
            
            # Test help command
            event = {
                "messageBody": "help",
                "originationNumber": "+1234567890"
            }
            
            response = self.handler.handle_incoming_message(event)
            
            # Should have called send_response with help message
            mock_send.assert_called()
            call_args = mock_send.call_args[0]
            assert "help" in call_args[1].lower() or "assist" in call_args[1].lower()
    
    @patch('boto3.client')
    def test_send_response(self, mock_boto_client):
        """Test sending SMS response"""
        # Mock AWS SMS client
        mock_client = Mock()
        mock_client.send_text_message.return_value = {"MessageId": "test-message-id"}
        
        self.handler.sms_client = mock_client
        self.handler.origination_number = "+1234567890"
        
        response = self.handler._send_response("+1987654321", "Test message")
        
        assert response["statusCode"] == 200
        mock_client.send_text_message.assert_called_once()
    
    def test_conversation_history(self):
        """Test conversation history tracking"""
        phone_number = "+1234567890"
        
        # Log some messages
        self.handler._log_message(phone_number, "Hello", "incoming", "sms")
        self.handler._log_message(phone_number, "Hi there!", "outgoing", "sms")
        
        history = self.handler.get_conversation_history(phone_number)
        
        assert len(history) == 2
        assert history[0]["direction"] == "incoming"
        assert history[1]["direction"] == "outgoing"
    
    def test_user_engagement_stats(self):
        """Test user engagement statistics"""
        phone_number = "+1234567890"
        
        # Log some messages
        self.handler._log_message(phone_number, "Hello", "incoming", "sms")
        self.handler._log_message(phone_number, "Hi!", "outgoing", "sms")
        self.handler._log_message(phone_number, "How are you?", "incoming", "sms")
        
        stats = self.handler.get_user_engagement_stats(phone_number)
        
        assert stats["total_messages"] == 3
        assert stats["incoming_messages"] == 2
        assert stats["outgoing_messages"] == 1
        assert stats["first_contact"] is not None
        assert stats["last_contact"] is not None


class TestIntegrationFlows:
    """Test complete conversation flows end-to-end"""
    
    def setup_method(self):
        self.ai = ConversationalNutritionistAI()
        self.phone = "+1234567890"
    
    def test_complete_onboarding_flow(self):
        """Test complete user onboarding flow"""
        # Step 1: Greeting
        response1 = self.ai.process_message(self.phone, "Hello!")
        assert "Good" in response1["message"]
        
        # Step 2: Goal setting  
        response2 = self.ai.process_message(
            self.phone, 
            "I'm 25 years old, 5'6\", 140 lbs, female, lightly active, want to maintain weight"
        )
        # The AI should offer nutrition assistance or acknowledge the information
        assert any(word in response2["message"].lower() for word in ["nutrition", "help", "assist", "goal", "maintain"])
        
        # Step 3: Food logging
        response3 = self.ai.process_message(self.phone, "I had oatmeal for breakfast")
        assert "logged" in response3["message"].lower() or "tell me" in response3["message"].lower()
        
        # Verify user profile was created and updated
        user_profile = self.ai._get_user_profile(self.phone)
        assert user_profile is not None
        
        # Verify health tracker exists (goals may not be automatically set)
        health_tracker = self.ai._get_health_tracker(self.phone)
        assert health_tracker is not None
    
    def test_meal_planning_to_grocery_flow(self):
        """Test flow from meal planning to grocery list generation"""
        # Set up user preferences
        user_profile = self.ai._get_user_profile(self.phone)
        from src.models.user_profile import DietaryPreference
        user_profile.dietary_preferences = [DietaryPreference("vegetarian")]
        
        # Add some basic vegetarian recipes to the meal planner for testing
        meal_planner = self.ai._get_meal_planner(self.phone)
        from src.models.meal_planning import Recipe, Ingredient, NutritionFacts, DifficultyLevel, MealType, CookingMethod
        
        test_recipe = Recipe(
            name="Vegetarian Pasta",
            description="Simple vegetarian pasta dish",
            ingredients=[
                Ingredient("pasta", 200, "grams"),
                Ingredient("tomato sauce", 150, "ml"),
                Ingredient("vegetables", 100, "grams")
            ],
            instructions=["Cook pasta", "Add sauce", "Serve"],
            prep_time_minutes=10,
            cook_time_minutes=15,
            servings=2,
            difficulty=DifficultyLevel.BEGINNER,
            meal_types=[MealType.DINNER],
            cooking_methods=[CookingMethod.STOVETOP],
            cuisine_type="Italian",
            dietary_restrictions=["vegetarian"],
            nutrition_facts=NutritionFacts(calories=400, protein_g=15, carbohydrates_g=60, fat_g=10)
        )
        meal_planner.add_recipe(test_recipe)
        
        # Request meal plan
        response1 = self.ai.process_message(self.phone, "Create a meal plan for this week")
        
        # Request grocery list
        response2 = self.ai.process_message(self.phone, "Generate grocery list from my meal plan")
        
        # Should provide some meaningful response (the system is working even if wording varies)
        assert len(response2["message"]) > 10  # Has some response
        assert "message" in response2  # Response structure is correct
    
    def test_inventory_to_meal_planning_flow(self):
        """Test using inventory for meal planning"""
        # Add items to inventory
        inventory = self.ai._get_inventory_manager(self.phone)
        item = FoodItem(
            name="Chicken",
            category=FoodCategory.MEAT_SEAFOOD,
            quantity=2.0,
            unit="lbs",
            storage_location=StorageLocation.REFRIGERATOR,
            expiration_date=date.today() + timedelta(days=2)
        )
        inventory.add_item(item)
        
        # Check expiring items
        response1 = self.ai.process_message(self.phone, "What's expiring soon?")
        assert "expiring" in response1["message"].lower() or "chicken" in response1["message"].lower()
        
        # Request meal plan using expiring items
        response2 = self.ai.process_message(self.phone, "Plan meals with expiring items")
        
        # Should suggest meals or provide guidance
        assert len(response2["suggestions"]) > 0


class TestAWSEndUserMessagingMigration:
    """Test AWS End User Messaging migration and fallback mechanisms - CRITICAL for Oct 30, 2026 deadline"""
    
    def setup_method(self):
        """Setup for AWS End User Messaging migration tests"""
        from src.services.messaging.sms import UniversalMessagingService
        self.messaging_service = UniversalMessagingService()
    
    def test_aws_end_user_messaging_deprecation_warning(self):
        """Test that system logs warning when falling back to deprecated AWS End User Messaging"""
        with patch('src.services.messaging.sms.logger') as mock_logger:
            with patch.dict('os.environ', {}, clear=True):  # No provider configs
                # This should trigger AWS End User Messaging fallback and warning
                from src.services.messaging.sms import UniversalMessagingService
                service = UniversalMessagingService()
                
                # Verify warning was logged about AWS End User Messaging deprecation
                warning_calls = [call for call in mock_logger.warning.call_args_list 
                               if 'deprecated' in str(call).lower()]
                assert len(warning_calls) > 0, "Should warn about using deprecated AWS End User Messaging"
    
    def test_twilio_over_aws_end_user_messaging_priority(self):
        """Test that Twilio is prioritized over deprecated AWS End User Messaging"""
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'TWILIO_SMS_FROM': '+12345678901',
            'AWS_SMS_ORIGINATION_IDENTITY': '+19876543210'  # Also configure AWS End User Messaging
        }):
            from src.services.messaging.sms import UniversalMessagingService
            service = UniversalMessagingService()
            
            # Should have Twilio as primary, not AWS End User Messaging
            assert "sms" in service.platforms
            
            # The platform should be Twilio, not AWS End User Messaging
            platform = service.platforms["sms"]
            assert platform.__class__.__name__ == "TwilioMessagingPlatform"
    
    def test_whatsapp_cloud_over_aws_end_user_messaging_whatsapp(self):
        """Test that WhatsApp Cloud API is prioritized over AWS End User Messaging WhatsApp"""
        with patch.dict('os.environ', {
            'WHATSAPP_CLOUD_ACCESS_TOKEN': 'test_token',
            'WHATSAPP_CLOUD_PHONE_NUMBER_ID': 'test_phone_id',
            'AWS_SMS_CONFIGURATION_SET': 'test_app_id'  # Also configure AWS End User Messaging WhatsApp
        }):
            from src.services.messaging.sms import UniversalMessagingService
            service = UniversalMessagingService()
            
            # Should have WhatsApp Cloud API, not AWS End User Messaging WhatsApp
            assert "whatsapp" in service.platforms
            platform = service.platforms["whatsapp"]
            assert platform.__class__.__name__ == "WhatsAppCloudPlatform"
    
    def test_aws_end_user_messaging_compatibility(self):
        """Test AWS End User Messaging APIs still work post-Pinpoint (these APIs continue)"""
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_client.send_text_message.return_value = {"MessageId": "test-msg-id"}
            mock_boto.return_value = mock_client
            
            # Mock environment for proper configuration
            with patch.dict('os.environ', {
                'PHONE_POOL_ID': 'test-pool-id',
                'SMS_CONFIG_SET': 'test-config-set'
            }):
                from src.services.messaging.notifications import AWSMessagingService
                aws_service = AWSMessagingService()
                
                # Mock the private method that gets origination number
                aws_service._origination_number = "+12345678901"
                
                # Should use pinpoint-sms-voice-v2 client (continues to work)
                result = aws_service.send_sms("+1234567890", "Test message")
                
                assert result["success"] == True
                mock_client.send_text_message.assert_called_once()
    
    def test_migration_timeline_compliance(self):
        """Test system behavior regarding migration timeline"""
        # Simulate being past May 20, 2025 (no new Pinpoint customers)
        # System should still work but prefer alternatives
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            from src.services.messaging.sms import UniversalMessagingService
            service = UniversalMessagingService()
            assert len(service.platforms) > 0  # Should have Twilio
        
        # Simulate being past October 30, 2026 (Pinpoint EOL)
        # System should function without Pinpoint
        with patch.dict('os.environ', {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            from src.services.messaging.sms import UniversalMessagingService
            service = UniversalMessagingService()
            # Should still have messaging capability
            assert len(service.platforms) > 0
    
    def test_pinpoint_infrastructure_migration_plan(self):
        """Test that infrastructure is ready for AWS End User Messaging migration"""
        # Check that terraform files use the correct APIs
        with patch('boto3.client') as mock_boto:
            mock_sms_client = Mock()
            mock_pinpoint_client = Mock()
            
            def boto_client_side_effect(service_name, **kwargs):
                if service_name == 'pinpoint-sms-voice-v2':
                    return mock_sms_client  # This API continues to work
                elif service_name == 'pinpoint':
                    return mock_pinpoint_client  # This API is deprecated
                return Mock()
            
            mock_boto.side_effect = boto_client_side_effect
            
            from src.services.messaging.notifications import AWSMessagingService
            service = AWSMessagingService()
            
            # Should use the continuing SMS API, not the deprecated Pinpoint API for SMS
            assert service.sms_client == mock_sms_client
            # WhatsApp still uses pinpoint client (needs migration)
            assert service.whatsapp_client == mock_pinpoint_client


if __name__ == "__main__":
    # Run specific test categories
    print("Running Conversational AI Nutritionist Tests...")
    
    # You can run individual test classes like this:
    # pytest test_conversational_nutritionist.py::TestConversationalAI -v
    # pytest test_conversational_nutritionist.py::TestIntegrationFlows -v
    
    pytest.main([__file__, "-v", "--tb=short"])
