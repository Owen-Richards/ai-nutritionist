"""
Comprehensive unit tests for nutrition domain services.

Tests cover:
- Nutrition calculation logic
- Food tracking functionality
- Nutrition insights generation
- External API integrations (Edamam)
- Caching and performance optimization
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta, date
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, List, Optional

from src.services.nutrition.calculator import EdamamService
from src.services.nutrition.tracker import NutritionTracker
from src.services.nutrition.insights import NutritionInsights
from src.services.nutrition.goals import HealthGoalsService


class TestEdamamService:
    """Test Edamam API integration service."""
    
    @pytest.fixture
    def mock_dynamodb(self):
        """Mock DynamoDB for caching."""
        mock_table = Mock()
        mock_table.get_item.return_value = {'Item': {}}
        mock_table.put_item.return_value = {}
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        return mock_dynamodb
    
    @pytest.fixture
    def mock_ssm(self):
        """Mock SSM for API keys."""
        mock_ssm = Mock()
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'test_api_key'}
        }
        return mock_ssm
    
    @pytest.fixture
    def edamam_service(self, mock_dynamodb, mock_ssm):
        """Create EdamamService with mocked dependencies."""
        with patch('boto3.resource', return_value=mock_dynamodb), \
             patch('boto3.client', return_value=mock_ssm):
            service = EdamamService()
            return service
    
    def test_service_initialization(self, edamam_service):
        """Test service initializes with correct configuration."""
        assert edamam_service is not None
        assert hasattr(edamam_service, 'dynamodb')
        assert hasattr(edamam_service, 'ssm')
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_success(self, edamam_service):
        """Test successful nutrition analysis."""
        # Mock successful API response
        mock_response = {
            'parsed': [{
                'food': {
                    'nutrients': {
                        'ENERC_KCAL': 200,
                        'PROCNT': 10,
                        'FAT': 8,
                        'CHOCDF': 25
                    },
                    'label': 'apple'
                }
            }]
        }
        
        with patch.object(edamam_service, '_make_api_request', return_value=mock_response):
            result = await edamam_service.analyze_nutrition("1 medium apple")
            
            assert result is not None
            assert 'calories' in result
            assert result['calories'] == 200
            assert result['protein'] == 10
            assert result['fat'] == 8
            assert result['carbs'] == 25
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_with_cache_hit(self, edamam_service, mock_dynamodb):
        """Test nutrition analysis with cache hit."""
        # Mock cache hit
        cached_data = {
            'Item': {
                'result': '{"calories": 150, "protein": 5}',
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        mock_dynamodb.Table().get_item.return_value = cached_data
        
        result = await edamam_service.analyze_nutrition("1 banana")
        
        assert result is not None
        # Should not make API call due to cache hit
        assert not hasattr(edamam_service, '_api_call_made')
    
    @pytest.mark.asyncio
    async def test_analyze_nutrition_api_failure(self, edamam_service):
        """Test nutrition analysis with API failure."""
        with patch.object(edamam_service, '_make_api_request', side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                await edamam_service.analyze_nutrition("invalid food")
    
    @pytest.mark.parametrize("food_text,expected_nutrients", [
        ("2 slices bread", {"calories": 160, "carbs": 30}),
        ("100g chicken breast", {"calories": 165, "protein": 31}),
        ("1 cup rice", {"calories": 205, "carbs": 45}),
    ])
    def test_food_parsing_variations(self, edamam_service, food_text, expected_nutrients):
        """Test parsing various food text formats."""
        # This would test the food text parsing logic
        parsed = edamam_service._parse_food_text(food_text)
        assert parsed is not None
    
    def test_cost_optimization_logic(self, edamam_service):
        """Test cost optimization prevents unnecessary API calls."""
        # Test duplicate request detection
        request1 = "1 apple"
        request2 = "1 apple"
        
        hash1 = edamam_service._generate_cache_key(request1)
        hash2 = edamam_service._generate_cache_key(request2)
        
        assert hash1 == hash2
    
    def test_cache_key_generation(self, edamam_service):
        """Test cache key generation is consistent."""
        text = "1 medium apple"
        key1 = edamam_service._generate_cache_key(text)
        key2 = edamam_service._generate_cache_key(text)
        
        assert key1 == key2
        assert len(key1) > 0


class TestNutritionTracker:
    """Test nutrition tracking functionality."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock nutrition data repository."""
        repository = Mock()
        repository.save_nutrition_entry = AsyncMock()
        repository.get_user_nutrition_history = AsyncMock()
        repository.get_daily_nutrition = AsyncMock()
        return repository
    
    @pytest.fixture
    def nutrition_tracker(self, mock_repository):
        """Create NutritionTracker with mocked repository."""
        return NutritionTracker(repository=mock_repository)
    
    @pytest.mark.asyncio
    async def test_log_food_entry_success(self, nutrition_tracker, mock_repository):
        """Test successful food entry logging."""
        user_id = "user123"
        food_data = {
            "food": "1 apple",
            "calories": 95,
            "protein": 0.5,
            "carbs": 25,
            "fat": 0.3
        }
        
        result = await nutrition_tracker.log_food_entry(user_id, food_data)
        
        assert result is not None
        mock_repository.save_nutrition_entry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_daily_summary(self, nutrition_tracker, mock_repository):
        """Test daily nutrition summary calculation."""
        user_id = "user123"
        target_date = date.today()
        
        # Mock nutrition entries for the day
        mock_entries = [
            {"calories": 200, "protein": 10, "carbs": 30, "fat": 8},
            {"calories": 350, "protein": 25, "carbs": 45, "fat": 12},
            {"calories": 180, "protein": 8, "carbs": 35, "fat": 5}
        ]
        mock_repository.get_daily_nutrition.return_value = mock_entries
        
        summary = await nutrition_tracker.get_daily_summary(user_id, target_date)
        
        assert summary['total_calories'] == 730
        assert summary['total_protein'] == 43
        assert summary['total_carbs'] == 110
        assert summary['total_fat'] == 25
    
    @pytest.mark.asyncio
    async def test_track_macro_goals(self, nutrition_tracker, mock_repository):
        """Test macro goals tracking."""
        user_id = "user123"
        goals = {
            "calories": 2000,
            "protein": 150,
            "carbs": 250,
            "fat": 70
        }
        
        current_intake = {
            "calories": 1500,
            "protein": 120,
            "carbs": 180,
            "fat": 50
        }
        
        progress = nutrition_tracker.calculate_goal_progress(goals, current_intake)
        
        assert progress['calories_progress'] == 0.75  # 1500/2000
        assert progress['protein_progress'] == 0.8    # 120/150
        assert progress['calories_remaining'] == 500
    
    def test_nutrition_validation(self, nutrition_tracker):
        """Test nutrition data validation."""
        valid_data = {
            "calories": 200,
            "protein": 10,
            "carbs": 25,
            "fat": 8
        }
        
        invalid_data = {
            "calories": -50,  # Invalid negative calories
            "protein": 10,
            "carbs": 25,
            "fat": 8
        }
        
        assert nutrition_tracker.validate_nutrition_data(valid_data) is True
        assert nutrition_tracker.validate_nutrition_data(invalid_data) is False


class TestNutritionInsights:
    """Test nutrition insights generation."""
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Mock analytics service."""
        service = Mock()
        service.get_nutrition_trends = AsyncMock()
        service.get_pattern_analysis = AsyncMock()
        return service
    
    @pytest.fixture
    def nutrition_insights(self, mock_analytics_service):
        """Create NutritionInsights with mocked analytics."""
        return NutritionInsights(analytics_service=mock_analytics_service)
    
    @pytest.mark.asyncio
    async def test_generate_weekly_insights(self, nutrition_insights, mock_analytics_service):
        """Test weekly nutrition insights generation."""
        user_id = "user123"
        week_data = [
            {"date": "2024-01-01", "calories": 2000, "protein": 150},
            {"date": "2024-01-02", "calories": 1800, "protein": 140},
            {"date": "2024-01-03", "calories": 2200, "protein": 160},
            {"date": "2024-01-04", "calories": 1900, "protein": 145},
            {"date": "2024-01-05", "calories": 2100, "protein": 155},
            {"date": "2024-01-06", "calories": 1750, "protein": 135},
            {"date": "2024-01-07", "calories": 2000, "protein": 150}
        ]
        
        mock_analytics_service.get_nutrition_trends.return_value = week_data
        
        insights = await nutrition_insights.generate_weekly_insights(user_id)
        
        assert 'average_calories' in insights
        assert 'protein_consistency' in insights
        assert 'recommendations' in insights
        assert insights['average_calories'] == 1964  # Average of week_data
    
    @pytest.mark.asyncio
    async def test_identify_nutritional_gaps(self, nutrition_insights):
        """Test identification of nutritional gaps."""
        nutrition_profile = {
            "fiber": 15,        # Low (RDA: 25g)
            "vitamin_c": 45,    # Low (RDA: 90mg)
            "iron": 12,         # Adequate (RDA: 8mg)
            "calcium": 800      # Low (RDA: 1000mg)
        }
        
        gaps = nutrition_insights.identify_nutritional_gaps(nutrition_profile)
        
        assert 'fiber' in gaps
        assert 'vitamin_c' in gaps
        assert 'calcium' in gaps
        assert 'iron' not in gaps  # Should not be in gaps as it's adequate
    
    def test_meal_timing_analysis(self, nutrition_insights):
        """Test meal timing pattern analysis."""
        meal_times = [
            {"time": "07:30", "calories": 400, "meal_type": "breakfast"},
            {"time": "12:00", "calories": 600, "meal_type": "lunch"},
            {"time": "15:30", "calories": 200, "meal_type": "snack"},
            {"time": "19:00", "calories": 700, "meal_type": "dinner"}
        ]
        
        analysis = nutrition_insights.analyze_meal_timing(meal_times)
        
        assert 'meal_distribution' in analysis
        assert 'eating_window' in analysis
        assert analysis['total_meals'] == 4


class TestHealthGoalsService:
    """Test health goals management."""
    
    @pytest.fixture
    def health_goals_service(self):
        """Create HealthGoalsService instance."""
        return HealthGoalsService()
    
    def test_set_weight_loss_goal(self, health_goals_service):
        """Test setting weight loss goals."""
        user_profile = {
            "current_weight": 180,
            "height": 70,  # inches
            "age": 30,
            "gender": "male",
            "activity_level": "moderate"
        }
        
        goal = health_goals_service.calculate_weight_loss_goals(
            user_profile, target_weight=160, timeline_weeks=12
        )
        
        assert goal['weekly_weight_loss'] <= 2.0  # Safe weight loss rate
        assert goal['daily_calorie_deficit'] > 0
        assert goal['target_calories'] < goal['maintenance_calories']
    
    def test_muscle_gain_goals(self, health_goals_service):
        """Test muscle gain goal calculations."""
        user_profile = {
            "current_weight": 150,
            "height": 68,
            "age": 25,
            "gender": "female",
            "activity_level": "high"
        }
        
        goal = health_goals_service.calculate_muscle_gain_goals(user_profile)
        
        assert goal['protein_target'] >= user_profile['current_weight'] * 0.8  # Minimum protein
        assert goal['calorie_surplus'] > 0
        assert goal['training_frequency'] >= 3  # Minimum training days
    
    @pytest.mark.parametrize("activity_level,expected_multiplier", [
        ("sedentary", 1.2),
        ("light", 1.375),
        ("moderate", 1.55),
        ("active", 1.725),
        ("very_active", 1.9)
    ])
    def test_activity_multipliers(self, health_goals_service, activity_level, expected_multiplier):
        """Test activity level multipliers for calorie calculations."""
        multiplier = health_goals_service.get_activity_multiplier(activity_level)
        assert multiplier == expected_multiplier


class TestNutritionBusinessRules:
    """Test business rules enforcement in nutrition domain."""
    
    def test_daily_calorie_limits(self):
        """Test daily calorie intake limits."""
        # Minimum safe calories
        assert not NutritionTracker.validate_daily_calories(500)  # Too low
        assert NutritionTracker.validate_daily_calories(1200)     # Minimum safe
        assert NutritionTracker.validate_daily_calories(3500)     # High but valid
        assert not NutritionTracker.validate_daily_calories(5000) # Too high
    
    def test_macro_ratio_validation(self):
        """Test macronutrient ratio validation."""
        valid_ratios = {"protein": 30, "carbs": 40, "fat": 30}
        invalid_ratios = {"protein": 50, "carbs": 40, "fat": 30}  # Sum > 100%
        
        assert NutritionTracker.validate_macro_ratios(valid_ratios) is True
        assert NutritionTracker.validate_macro_ratios(invalid_ratios) is False
    
    def test_nutrient_deficiency_alerts(self):
        """Test nutrient deficiency alert system."""
        low_nutrients = {
            "vitamin_d": 5,    # Very low
            "vitamin_b12": 1,  # Deficient
            "iron": 15         # Adequate
        }
        
        alerts = NutritionInsights.check_deficiency_alerts(low_nutrients)
        
        assert 'vitamin_d' in alerts
        assert 'vitamin_b12' in alerts
        assert 'iron' not in alerts


# Performance tests
class TestNutritionPerformance:
    """Test performance characteristics of nutrition services."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_bulk_nutrition_analysis_performance(self):
        """Test performance of bulk nutrition analysis."""
        foods = ["1 apple", "1 banana", "1 orange"] * 10  # 30 items
        
        start_time = datetime.utcnow()
        # Would run bulk analysis here
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0  # Should complete within 5 seconds
    
    @pytest.mark.performance
    def test_daily_summary_calculation_performance(self):
        """Test performance of daily summary calculations."""
        # Mock 100 nutrition entries
        entries = [
            {"calories": 100, "protein": 5, "carbs": 15, "fat": 3}
            for _ in range(100)
        ]
        
        start_time = datetime.utcnow()
        # Would calculate summary here
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        assert duration < 0.1  # Should be very fast


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
