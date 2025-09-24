"""Integration tests for Track D - Integrations.

Tests for Calendar, Grocery, and Fitness integration services.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.integrations import (
    CalendarProvider,
    FitnessProvider,
    GroceryExportFormat,
    CalendarEvent,
    GroceryList,
    GroceryItem,
    FitnessData,
    WorkoutSession,
    WorkoutType,
    OAuthCredentials
)
from src.services.integrations.calendar_service import CalendarService
from src.services.integrations.grocery_service import GroceryService
from src.services.integrations.fitness_service import FitnessService


class TestCalendarIntegration:
    """Test calendar integration (D1)."""

    @pytest.fixture
    def calendar_service(self):
        """Create calendar service instance."""
        return CalendarService()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    @pytest.fixture
    def meal_plan_id(self):
        """Create test meal plan ID."""
        return uuid4()

    def test_get_authorization_url_google(self, calendar_service, user_id):
        """Test Google Calendar OAuth URL generation."""
        redirect_uri = "https://app.example.com/callback"
        
        auth_url = calendar_service.get_authorization_url(
            user_id, CalendarProvider.GOOGLE, redirect_uri
        )
        
        assert "accounts.google.com/o/oauth2/auth" in auth_url
        assert "client_id" in auth_url
        assert "scope" in auth_url
        assert f"{user_id}:{CalendarProvider.GOOGLE.value}" in auth_url

    def test_get_authorization_url_outlook(self, calendar_service, user_id):
        """Test Outlook OAuth URL generation."""
        redirect_uri = "https://app.example.com/callback"
        
        auth_url = calendar_service.get_authorization_url(
            user_id, CalendarProvider.OUTLOOK, redirect_uri
        )
        
        assert "login.microsoftonline.com" in auth_url
        assert "client_id" in auth_url
        assert f"{user_id}:{CalendarProvider.OUTLOOK.value}" in auth_url

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_connect_google_calendar(self, mock_post, calendar_service, user_id):
        """Test Google Calendar OAuth flow."""
        # Mock token response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/calendar"
        }
        mock_post.return_value = mock_response
        
        credentials = await calendar_service.connect_calendar_provider(
            user_id, CalendarProvider.GOOGLE, "test_code", "https://app.example.com/callback"
        )
        
        assert credentials.user_id == user_id
        assert credentials.provider == CalendarProvider.GOOGLE
        assert credentials.access_token == "test_access_token"
        assert credentials.refresh_token == "test_refresh_token"
        assert user_id in calendar_service.credentials_store

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_create_meal_prep_events(self, mock_post, calendar_service, user_id, meal_plan_id):
        """Test meal prep event creation."""
        # Setup credentials
        credentials = OAuthCredentials(
            user_id=user_id,
            provider=CalendarProvider.GOOGLE,
            access_token="test_token",
            scope=["https://www.googleapis.com/auth/calendar"]
        )
        calendar_service.credentials_store[user_id] = credentials
        
        # Mock calendar API responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_event_id",
            "htmlLink": "https://calendar.google.com/event?eid=test"
        }
        mock_post.return_value = mock_response
        
        prep_event, cook_event = await calendar_service.create_meal_prep_events(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            prep_time_minutes=30,
            cook_time_minutes=45
        )
        
        assert prep_event.meal_plan_id == meal_plan_id
        assert prep_event.event_type.value == "meal_prep"
        assert prep_event.duration_minutes == 30
        assert cook_event.event_type.value == "meal_cook"
        assert cook_event.duration_minutes == 45
        assert prep_event.calendar_event_id is not None
        assert cook_event.calendar_event_id is not None

    def test_calendar_event_validation(self):
        """Test calendar event model validation."""
        user_id = uuid4()
        meal_plan_id = uuid4()
        
        # Valid event
        event = CalendarEvent(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            title="Meal Prep",
            start_time=datetime.now() + timedelta(hours=1),
            duration_minutes=30,
            provider=CalendarProvider.GOOGLE,
            calendar_event_id="test_id"
        )
        
        assert event.user_id == user_id
        assert event.meal_plan_id == meal_plan_id
        assert event.duration_minutes == 30

    @pytest.mark.asyncio
    async def test_calendar_without_credentials(self, calendar_service, user_id, meal_plan_id):
        """Test calendar operations without credentials."""
        with pytest.raises(ValueError, match="Calendar provider not connected"):
            await calendar_service.create_meal_prep_events(
                user_id=user_id,
                meal_plan_id=meal_plan_id,
                prep_time_minutes=30,
                cook_time_minutes=45
            )


class TestGroceryIntegration:
    """Test grocery integration (D2)."""

    @pytest.fixture
    def grocery_service(self):
        """Create grocery service instance."""
        return GroceryService()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    @pytest.fixture
    def meal_plan_id(self):
        """Create test meal plan ID."""
        return uuid4()

    @pytest.fixture
    def sample_grocery_list(self, user_id, meal_plan_id):
        """Create sample grocery list."""
        items = [
            GroceryItem(
                name="Chicken Breast",
                quantity=Decimal("2.0"),
                unit="lbs",
                category="Meat & Poultry",
                estimated_price=Decimal("12.99")
            ),
            GroceryItem(
                name="Brown Rice",
                quantity=Decimal("1.0"),
                unit="lb",
                category="Grains",
                estimated_price=Decimal("3.49")
            ),
            GroceryItem(
                name="Broccoli",
                quantity=Decimal("2.0"),
                unit="heads",
                category="Vegetables",
                estimated_price=Decimal("4.98")
            )
        ]
        
        return GroceryList(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            items=items,
            servings=4
        )

    @pytest.mark.asyncio
    async def test_generate_grocery_list(self, grocery_service, user_id, meal_plan_id):
        """Test grocery list generation from meal plan."""
        grocery_list = await grocery_service.generate_grocery_list(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            servings=4,
            consolidate_similar=True
        )
        
        assert grocery_list.user_id == user_id
        assert grocery_list.meal_plan_id == meal_plan_id
        assert grocery_list.servings == 4
        assert len(grocery_list.items) > 0
        assert grocery_list.estimated_total_cost > 0

    @pytest.mark.asyncio
    async def test_export_grocery_list_csv(self, grocery_service, sample_grocery_list):
        """Test CSV export of grocery list."""
        # Store the grocery list
        grocery_service.grocery_lists[sample_grocery_list.id] = sample_grocery_list
        
        csv_export = await grocery_service.export_grocery_list(
            user_id=sample_grocery_list.user_id,
            grocery_list_id=sample_grocery_list.id,
            format=GroceryExportFormat.CSV,
            include_quantities=True,
            include_categories=True
        )
        
        assert "Chicken Breast,2.0,lbs,Meat & Poultry" in csv_export
        assert "Brown Rice,1.0,lb,Grains" in csv_export
        assert "Broccoli,2.0,heads,Vegetables" in csv_export

    @pytest.mark.asyncio
    async def test_export_grocery_list_json(self, grocery_service, sample_grocery_list):
        """Test JSON export of grocery list."""
        import json
        
        # Store the grocery list
        grocery_service.grocery_lists[sample_grocery_list.id] = sample_grocery_list
        
        json_export = await grocery_service.export_grocery_list(
            user_id=sample_grocery_list.user_id,
            grocery_list_id=sample_grocery_list.id,
            format=GroceryExportFormat.JSON,
            include_quantities=True,
            include_categories=True
        )
        
        data = json.loads(json_export)
        assert "items" in data
        assert len(data["items"]) == 3
        assert data["items"][0]["name"] == "Chicken Breast"

    @pytest.mark.asyncio
    async def test_export_grocery_list_markdown(self, grocery_service, sample_grocery_list):
        """Test Markdown export of grocery list."""
        # Store the grocery list
        grocery_service.grocery_lists[sample_grocery_list.id] = sample_grocery_list
        
        md_export = await grocery_service.export_grocery_list(
            user_id=sample_grocery_list.user_id,
            grocery_list_id=sample_grocery_list.id,
            format=GroceryExportFormat.MARKDOWN,
            include_quantities=True,
            include_categories=True
        )
        
        assert "# Grocery List" in md_export
        assert "## Meat & Poultry" in md_export
        assert "- Chicken Breast: 2.0 lbs" in md_export

    @pytest.mark.asyncio
    async def test_generate_partner_deeplinks(self, grocery_service, sample_grocery_list):
        """Test partner deeplink generation."""
        # Store the grocery list
        grocery_service.grocery_lists[sample_grocery_list.id] = sample_grocery_list
        
        deeplinks = await grocery_service.generate_partner_deeplinks(
            user_id=sample_grocery_list.user_id,
            grocery_list_id=sample_grocery_list.id,
            preferred_partners=["instacart", "amazon_fresh"]
        )
        
        assert "instacart" in deeplinks
        assert "amazon_fresh" in deeplinks
        assert "instacart.com" in deeplinks["instacart"]
        assert "amazon.com/fresh" in deeplinks["amazon_fresh"]

    def test_grocery_item_consolidation(self, grocery_service):
        """Test ingredient consolidation logic."""
        items = [
            GroceryItem(name="Chicken Breast", quantity=Decimal("1.0"), unit="lb"),
            GroceryItem(name="Chicken Breast", quantity=Decimal("1.5"), unit="lb"),
            GroceryItem(name="Olive Oil", quantity=Decimal("0.25"), unit="cup"),
            GroceryItem(name="Extra Virgin Olive Oil", quantity=Decimal("0.5"), unit="cup")
        ]
        
        consolidated = grocery_service.list_generator._consolidate_ingredients(items)
        
        # Should consolidate exact matches
        chicken_items = [item for item in consolidated if "Chicken" in item.name]
        assert len(chicken_items) == 1
        assert chicken_items[0].quantity == Decimal("2.5")
        
        # Should not consolidate similar but different items
        oil_items = [item for item in consolidated if "Oil" in item.name]
        assert len(oil_items) == 2

    def test_grocery_item_categorization(self, grocery_service):
        """Test ingredient categorization."""
        categorizer = grocery_service.list_generator
        
        assert categorizer._categorize_ingredient("chicken breast") == "Meat & Poultry"
        assert categorizer._categorize_ingredient("salmon fillet") == "Seafood"
        assert categorizer._categorize_ingredient("broccoli") == "Vegetables"
        assert categorizer._categorize_ingredient("brown rice") == "Grains"
        assert categorizer._categorize_ingredient("unknown ingredient") == "Other"


class TestFitnessIntegration:
    """Test fitness integration (D3)."""

    @pytest.fixture
    def fitness_service(self):
        """Create fitness service instance."""
        service = FitnessService()
        service.fitness_enabled = True  # Ensure feature is enabled for tests
        return service

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    @pytest.fixture
    def sample_fitness_data(self, user_id):
        """Create sample fitness data."""
        return FitnessData(
            user_id=user_id,
            date=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            provider=FitnessProvider.GOOGLE_FIT,
            steps=8500,
            distance_km=Decimal("6.8"),
            calories_burned=450,
            active_minutes=65,
            resting_heart_rate=68,
            sleep_hours=Decimal("7.5"),
            workouts=[
                WorkoutSession(
                    workout_type=WorkoutType.RUNNING,
                    duration_minutes=35,
                    calories_burned=320,
                    intensity="moderate"
                )
            ]
        )

    def test_fitness_feature_flag(self, fitness_service):
        """Test fitness feature flag functionality."""
        assert fitness_service.is_enabled() == True
        
        fitness_service.fitness_enabled = False
        assert fitness_service.is_enabled() == False

    def test_get_authorization_url_google_fit(self, fitness_service, user_id):
        """Test Google Fit OAuth URL generation."""
        redirect_uri = "https://app.example.com/callback"
        
        auth_url = fitness_service.get_authorization_url(
            user_id, FitnessProvider.GOOGLE_FIT, redirect_uri
        )
        
        assert "accounts.google.com/o/oauth2/auth" in auth_url
        assert "fitness.activity.read" in auth_url
        assert f"{user_id}:{FitnessProvider.GOOGLE_FIT.value}" in auth_url

    def test_get_authorization_url_fitbit(self, fitness_service, user_id):
        """Test Fitbit OAuth URL generation."""
        redirect_uri = "https://app.example.com/callback"
        
        auth_url = fitness_service.get_authorization_url(
            user_id, FitnessProvider.FITBIT, redirect_uri
        )
        
        assert "fitbit.com/oauth2/authorize" in auth_url
        assert f"{user_id}:{FitnessProvider.FITBIT.value}" in auth_url

    def test_apple_health_authorization(self, fitness_service, user_id):
        """Test Apple Health authorization (special case)."""
        auth_url = fitness_service.get_authorization_url(
            user_id, FitnessProvider.APPLE_HEALTH, "app://redirect"
        )
        
        assert auth_url == "app://health-kit-auth"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_connect_fitness_provider(self, mock_post, fitness_service, user_id):
        """Test fitness provider OAuth flow."""
        # Mock token response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "scope": "activity heartrate"
        }
        mock_post.return_value = mock_response
        
        credentials = await fitness_service.connect_fitness_provider(
            user_id, FitnessProvider.FITBIT, "test_code", "https://app.example.com/callback"
        )
        
        assert credentials.user_id == user_id
        assert credentials.provider == FitnessProvider.FITBIT
        assert credentials.access_token == "test_access_token"

    def test_fitness_data_activity_level_calculation(self, sample_fitness_data):
        """Test activity level calculation."""
        # Moderate activity
        sample_fitness_data.steps = 8500
        sample_fitness_data.active_minutes = 65
        assert sample_fitness_data.calculate_activity_level() == "moderate"
        
        # High activity
        sample_fitness_data.steps = 12000
        sample_fitness_data.active_minutes = 90
        assert sample_fitness_data.calculate_activity_level() == "high"
        
        # Very high activity
        sample_fitness_data.steps = 15000
        sample_fitness_data.active_minutes = 120
        assert sample_fitness_data.calculate_activity_level() == "very_high"

    def test_fitness_data_recovery_needs(self, sample_fitness_data):
        """Test recovery nutrition needs calculation."""
        # No recovery needed
        sample_fitness_data.workouts = []
        sample_fitness_data.calories_burned = 200
        assert sample_fitness_data.needs_recovery_nutrition() == False
        
        # Recovery needed - high intensity workout
        sample_fitness_data.workouts = [
            WorkoutSession(
                workout_type=WorkoutType.HIIT,
                duration_minutes=45,
                calories_burned=400,
                intensity="high"
            )
        ]
        assert sample_fitness_data.needs_recovery_nutrition() == True
        
        # Recovery needed - long endurance workout
        sample_fitness_data.workouts = [
            WorkoutSession(
                workout_type=WorkoutType.RUNNING,
                duration_minutes=90,
                calories_burned=600,
                intensity="moderate"
            )
        ]
        assert sample_fitness_data.needs_recovery_nutrition() == True

    def test_nutrition_adjustments(self, fitness_service, sample_fitness_data):
        """Test nutrition adjustment calculations."""
        # Store fitness data
        date_key = sample_fitness_data.date.strftime("%Y-%m-%d")
        fitness_service.fitness_data_store[(sample_fitness_data.user_id, date_key)] = sample_fitness_data
        
        adjustments = fitness_service.get_nutrition_adjustments(
            sample_fitness_data.user_id, sample_fitness_data.date, "high_protein"
        )
        
        assert adjustments is not None
        assert "calories_adjustment" in adjustments
        assert "protein_adjustment" in adjustments
        assert "reasoning" in adjustments
        assert len(adjustments["reasoning"]) > 0

    def test_weekly_activity_summary(self, fitness_service, user_id):
        """Test weekly activity summary calculation."""
        # Create sample week of data
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(7):
            date = today - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            
            fitness_data = FitnessData(
                user_id=user_id,
                date=date,
                provider=FitnessProvider.GOOGLE_FIT,
                steps=8000 + (i * 500),
                calories_burned=400 + (i * 50),
                sleep_hours=Decimal("7.5"),
                workouts=[
                    WorkoutSession(
                        workout_type=WorkoutType.RUNNING,
                        duration_minutes=30,
                        calories_burned=250
                    )
                ]
            )
            
            fitness_service.fitness_data_store[(user_id, date_key)] = fitness_data
        
        summary = fitness_service.calculate_weekly_activity_summary(user_id)
        
        assert summary["total_steps"] > 0
        assert summary["total_calories"] > 0
        assert summary["total_workouts"] == 7
        assert summary["weekly_consistency"] == 1.0  # 7/7 days
        assert len(summary["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_fitness_disabled_operations(self, fitness_service, user_id):
        """Test operations when fitness integration is disabled."""
        fitness_service.fitness_enabled = False
        
        # Should return None/empty when disabled
        assert fitness_service.sync_daily_fitness_data(user_id) is None
        assert fitness_service.get_fitness_data(user_id, datetime.now()) is None
        assert fitness_service.get_nutrition_adjustments(user_id, datetime.now()) is None
        assert fitness_service.get_user_fitness_history(user_id) == []
        
        # Should raise error for auth operations
        with pytest.raises(ValueError, match="Fitness integration is disabled"):
            fitness_service.get_authorization_url(user_id, FitnessProvider.GOOGLE_FIT, "https://test.com")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    @patch('httpx.AsyncClient.get')
    async def test_google_fit_data_import(self, mock_get, mock_post, fitness_service, user_id):
        """Test Google Fit data import."""
        # Setup credentials
        credentials = OAuthCredentials(
            user_id=user_id,
            provider=FitnessProvider.GOOGLE_FIT,
            access_token="test_token",
            scope=["fitness.activity.read"]
        )
        
        # Mock API responses
        steps_response = MagicMock()
        steps_response.status_code = 200
        steps_response.json.return_value = {
            "bucket": [{
                "dataset": [{
                    "point": [{"value": [{"intVal": 8500}]}]
                }]
            }]
        }
        
        calories_response = MagicMock()
        calories_response.status_code = 200
        calories_response.json.return_value = {
            "bucket": [{
                "dataset": [{
                    "point": [{"value": [{"fpVal": 450.0}]}]
                }]
            }]
        }
        
        mock_post.side_effect = [steps_response, calories_response]
        
        fitness_data = await fitness_service.data_importer._import_google_fit_data(
            credentials, datetime.now()
        )
        
        assert fitness_data.steps == 8500
        assert fitness_data.calories_burned == 450
        assert fitness_data.provider == FitnessProvider.GOOGLE_FIT


class TestIntegrationWorkflows:
    """Test complete integration workflows."""

    @pytest.fixture
    def services(self):
        """Create all integration services."""
        return {
            "calendar": CalendarService(),
            "grocery": GroceryService(),
            "fitness": FitnessService()
        }

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_meal_planning_workflow(self, services, user_id):
        """Test complete meal planning integration workflow."""
        meal_plan_id = uuid4()
        
        # 1. Generate grocery list
        grocery_list = await services["grocery"].generate_grocery_list(
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            servings=4
        )
        assert grocery_list is not None
        
        # 2. Export grocery list
        csv_export = await services["grocery"].export_grocery_list(
            user_id=user_id,
            grocery_list_id=grocery_list.id,
            format=GroceryExportFormat.CSV
        )
        assert len(csv_export) > 0
        
        # 3. Get partner deeplinks
        deeplinks = await services["grocery"].generate_partner_deeplinks(
            user_id=user_id,
            grocery_list_id=grocery_list.id
        )
        assert len(deeplinks) > 0

    @pytest.mark.asyncio
    async def test_fitness_nutrition_workflow(self, services, user_id):
        """Test fitness-driven nutrition adjustment workflow."""
        today = datetime.now()
        
        # 1. Simulate fitness data
        fitness_data = FitnessData(
            user_id=user_id,
            date=today,
            provider=FitnessProvider.GOOGLE_FIT,
            steps=12000,
            calories_burned=600,
            active_minutes=90,
            workouts=[
                WorkoutSession(
                    workout_type=WorkoutType.HIIT,
                    duration_minutes=45,
                    calories_burned=400,
                    intensity="high"
                )
            ]
        )
        
        # Store the data
        date_key = today.strftime("%Y-%m-%d")
        services["fitness"].fitness_data_store[(user_id, date_key)] = fitness_data
        
        # 2. Get nutrition adjustments
        adjustments = services["fitness"].get_nutrition_adjustments(
            user_id, today, "high_protein"
        )
        
        assert adjustments is not None
        assert adjustments["calories_adjustment"] > 0
        assert adjustments["recovery_focus"] == True
        assert len(adjustments["meal_suggestions"]) > 0

    def test_integration_status_check(self, services, user_id):
        """Test integration status checking."""
        # Initially no connections
        calendar_connected = user_id in services["calendar"].credentials_store
        fitness_connected = user_id in services["fitness"].credentials_store
        
        assert calendar_connected == False
        assert fitness_connected == False
        
        # Add credentials
        services["calendar"].credentials_store[user_id] = OAuthCredentials(
            user_id=user_id,
            provider=CalendarProvider.GOOGLE,
            access_token="test_token",
            scope=["calendar"]
        )
        
        # Check updated status
        calendar_connected = user_id in services["calendar"].credentials_store
        assert calendar_connected == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
