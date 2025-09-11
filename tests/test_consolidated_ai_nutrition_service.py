"""
Test Suite for Consolidated AI & Nutrition Service
Validates unified AI-powered meal planning, nutrition analysis, and user profiling
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

import boto3

from src.services.consolidated_ai_nutrition_service import (
    ConsolidatedAINutritionService,
    DayNutrition,
    UserProfile
)


class TestConsolidatedAINutritionService:
    """Test the consolidated AI & nutrition service functionality"""
    
    @pytest.fixture
    def mock_aws_services(self):
        """Mock AWS services for testing"""
        with patch('boto3.client') as mock_client:
            with patch('boto3.resource') as mock_resource:
                # Mock Bedrock client
                mock_bedrock = Mock()
                mock_bedrock.invoke_model.return_value = {
                    'body': Mock(read=lambda: json.dumps({
                        'results': [{'outputText': 'Test AI response'}]
                    }).encode())
                }
                
                # Mock DynamoDB tables
                mock_table = Mock()
                mock_table.put_item.return_value = {}
                mock_table.get_item.return_value = {'Item': {'data': json.dumps({'test': 'data'})}}
                mock_table.query.return_value = {'Items': []}
                
                mock_resource.return_value.Table.return_value = mock_table
                mock_client.return_value = mock_bedrock
                
                yield {
                    'bedrock': mock_bedrock,
                    'table': mock_table
                }
    
    @pytest.fixture
    def service(self, mock_aws_services):
        """Create service instance with mocked dependencies"""
        with patch.object(ConsolidatedAINutritionService, '_get_parameter') as mock_param:
            mock_param.return_value = 'test_key'
            return ConsolidatedAINutritionService()
    
    @pytest.fixture
    def sample_user_profile(self):
        """Sample user profile for testing"""
        return {
            'user_id': 'test_user_123',
            'dietary_restrictions': ['vegetarian'],
            'allergies': ['nuts'],
            'household_size': 2,
            'weekly_budget': 75.0,
            'fitness_goals': 'weight_loss',
            'daily_calories': 1800,
            'health_conditions': [],
            'cooking_skill': 'intermediate'
        }
    
    @pytest.fixture
    def sample_nutrition_data(self):
        """Sample nutrition data for testing"""
        return DayNutrition(
            date='2024-01-15',
            kcal=1650,
            protein=85,
            carbs=180,
            fat=55,
            fiber=25,
            sodium=1800,
            water_cups=7,
            mood='🙂',
            energy='⚡'
        )

    def test_init_service(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, 'bedrock_runtime')
        assert hasattr(service, 'dynamodb')
        assert hasattr(service, 'nutrition_strategies')
        assert 'intermittent_fasting' in service.nutrition_strategies

    def test_user_profile_dataclass(self):
        """Test UserProfile dataclass functionality"""
        profile = UserProfile(
            user_id='test_123',
            dietary_restrictions=['vegan'],
            daily_calories=2000
        )
        
        assert profile.user_id == 'test_123'
        assert profile.dietary_restrictions == ['vegan']
        assert profile.daily_calories == 2000
        assert profile.household_size == 2  # Default value
        assert profile.allergies == []  # Default empty list

    def test_day_nutrition_dataclass(self):
        """Test DayNutrition dataclass functionality"""
        nutrition = DayNutrition(
            date='2024-01-15',
            kcal=1800,
            protein=90
        )
        
        assert nutrition.date == '2024-01-15'
        assert nutrition.kcal == 1800
        assert nutrition.protein == 90
        assert nutrition.carbs == 0  # Default value
        assert nutrition.meals_ate == []  # Default empty list

    def test_generate_cache_key(self, service, sample_user_profile):
        """Test cache key generation for meal plans"""
        cache_key = service._generate_cache_key(sample_user_profile)
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5 hash length
        
        # Same profile should generate same key
        cache_key2 = service._generate_cache_key(sample_user_profile)
        assert cache_key == cache_key2
        
        # Different profile should generate different key
        different_profile = sample_user_profile.copy()
        different_profile['dietary_restrictions'] = ['vegan']
        cache_key3 = service._generate_cache_key(different_profile)
        assert cache_key != cache_key3

    def test_suggest_nutrition_strategy(self, service, sample_user_profile):
        """Test nutrition strategy suggestion logic"""
        # Weight loss goal should suggest intermittent fasting
        weight_loss_profile = sample_user_profile.copy()
        weight_loss_profile['fitness_goals'] = 'weight loss'
        strategy = service._suggest_nutrition_strategy(weight_loss_profile)
        assert strategy == 'intermittent_fasting'
        
        # Digestive issues should suggest gut health focus
        gut_health_profile = sample_user_profile.copy()
        gut_health_profile['health_conditions'] = ['ibs']
        gut_health_profile['fitness_goals'] = 'maintenance'  # Override weight loss
        strategy = service._suggest_nutrition_strategy(gut_health_profile)
        assert strategy == 'gut_health_focus'
        
        # Plant-based preferences should suggest plant-forward
        plant_profile = sample_user_profile.copy()
        plant_profile['dietary_restrictions'] = ['vegetarian']
        plant_profile['fitness_goals'] = 'maintenance'  # Override weight loss
        strategy = service._suggest_nutrition_strategy(plant_profile)
        assert strategy == 'plant_forward'
        
        # Default case should suggest time-restricted eating
        default_profile = sample_user_profile.copy()
        default_profile['fitness_goals'] = 'maintenance'
        default_profile['dietary_restrictions'] = []
        strategy = service._suggest_nutrition_strategy(default_profile)
        assert strategy == 'time_restricted_eating'

    @patch('src.services.consolidated_ai_nutrition_service.aiohttp.ClientSession')
    async def test_analyze_meal_nutrition(self, mock_session, service):
        """Test meal nutrition analysis"""
        # Mock Edamam API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'calories': 450,
            'totalWeight': 250,
            'totalNutrients': {
                'PROCNT': {'quantity': 25.5},
                'CHOCDF': {'quantity': 45.0},
                'FAT': {'quantity': 15.0},
                'FIBTG': {'quantity': 8.5},
                'NA': {'quantity': 650.0}
            },
            'totalDaily': {
                'PROCNT': {'quantity': 51.0},
                'VITC': {'quantity': 25.0}
            }
        })
        
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        ingredients = ['1 cup cooked quinoa', '1/2 cup black beans', '1 avocado']
        result = await service.analyze_meal_nutrition(ingredients, 'test_user')
        
        assert result['calories'] == 450
        assert result['macros']['protein'] == 25.5
        assert result['macros']['carbs'] == 45.0
        assert result['macros']['fat'] == 15.0
        assert result['macros']['fiber'] == 8.5
        assert result['minerals']['sodium'] == 650.0

    def test_extract_diet_labels(self, service, sample_user_profile):
        """Test extraction of Edamam diet labels from user profile"""
        # Test vegetarian restriction
        labels = service._extract_diet_labels(sample_user_profile)
        assert 'vegetarian' in labels
        
        # Test vegan restriction
        vegan_profile = sample_user_profile.copy()
        vegan_profile['dietary_restrictions'] = ['vegan']
        labels = service._extract_diet_labels(vegan_profile)
        assert 'vegan' in labels
        
        # Test multiple restrictions
        multi_profile = sample_user_profile.copy()
        multi_profile['dietary_restrictions'] = ['vegetarian', 'paleo']
        labels = service._extract_diet_labels(multi_profile)
        assert 'vegetarian' in labels
        assert 'paleo' in labels

    def test_extract_health_labels(self, service, sample_user_profile):
        """Test extraction of Edamam health labels from user profile"""
        # Test allergy-based labels
        labels = service._extract_health_labels(sample_user_profile)
        assert 'tree-nut-free' in labels  # From nuts allergy
        
        # Test health condition-based labels
        health_profile = sample_user_profile.copy()
        health_profile['health_conditions'] = ['diabetes', 'hypertension']
        labels = service._extract_health_labels(health_profile)
        assert 'low-sugar' in labels
        assert 'low-sodium' in labels

    def test_track_daily_nutrition(self, service, sample_nutrition_data):
        """Test daily nutrition tracking"""
        result = service.track_daily_nutrition('test_user', sample_nutrition_data)
        
        assert result['success'] is True
        assert 'insights' in result
        assert 'daily_summary' in result
        assert 'recommendations' in result
        
        # Check that insights are generated
        insights = result['insights']
        assert isinstance(insights, list)

    def test_format_recipe_for_whatsapp(self, service):
        """Test recipe formatting for WhatsApp"""
        recipe = {
            'label': 'Quinoa Buddha Bowl',
            'totalTime': 25,
            'yield': 4,
            'calories': 1800,
            'url': 'https://example.com/recipe'
        }
        
        formatted = service.format_recipe_for_whatsapp(recipe)
        
        assert 'Quinoa Buddha Bowl' in formatted
        assert '25 minutes' in formatted
        assert '4 servings' in formatted
        assert '450 calories per serving' in formatted  # 1800/4
        assert 'https://example.com/recipe' in formatted

    def test_format_nutrition_summary(self, service):
        """Test nutrition summary formatting"""
        nutrition_data = {
            'calories': 650,
            'macros': {
                'protein': 28,
                'carbs': 55,
                'fat': 22,
                'fiber': 12
            }
        }
        
        summary = service._format_nutrition_summary(nutrition_data)
        
        assert '650 calories' in summary
        assert '28g protein' in summary
        assert '55g carbs' in summary
        assert '22g fat' in summary
        assert '12g fiber' in summary

    def test_calculate_recipe_score(self, service, sample_user_profile):
        """Test recipe scoring based on user preferences"""
        recipe = {
            'dietLabels': ['vegetarian'],
            'totalTime': 25,
            'calories': 450,
            'yield': 1
        }
        
        score = service._calculate_recipe_score(recipe, sample_user_profile)
        
        # Should get points for vegetarian match and reasonable time
        assert score > 0
        assert isinstance(score, float)

    def test_calculate_recipe_difficulty(self, service):
        """Test recipe difficulty calculation"""
        # Easy recipe
        easy_recipe = {
            'totalTime': 15,
            'ingredients': ['banana', 'yogurt', 'honey']
        }
        difficulty = service._calculate_recipe_difficulty(easy_recipe, 'beginner')
        assert difficulty <= 2
        
        # Complex recipe
        complex_recipe = {
            'totalTime': 120,
            'ingredients': ['ingredient' + str(i) for i in range(20)]
        }
        difficulty = service._calculate_recipe_difficulty(complex_recipe, 'advanced')
        assert difficulty >= 4

    @pytest.mark.asyncio
    async def test_suggest_substitutions(self, service):
        """Test ingredient substitution suggestions"""
        # Test dairy substitution
        substitutions = await service.suggest_substitutions('milk', ['dairy-free'])
        assert len(substitutions) > 0
        assert any('almond milk' in sub for sub in substitutions)
        
        # Test vegan substitution
        substitutions = await service.suggest_substitutions('butter', ['vegan'])
        assert len(substitutions) > 0
        assert any('coconut oil' in sub for sub in substitutions)

    def test_analyze_nutrition_trends(self, service, sample_nutrition_data):
        """Test nutrition trend analysis"""
        insights = service._analyze_nutrition_trends('test_user', sample_nutrition_data)
        
        assert isinstance(insights, list)
        # Should not trigger low calorie warning (1650 > 1200)
        assert not any('Very low calorie' in insight for insight in insights)
        
        # Test low calorie scenario
        low_cal_nutrition = DayNutrition(date='2024-01-15', kcal=800)
        insights = service._analyze_nutrition_trends('test_user', low_cal_nutrition)
        assert any('Very low calorie' in insight for insight in insights)

    def test_get_daily_recommendations(self, service):
        """Test daily nutrition recommendations"""
        # Low protein scenario
        low_protein_nutrition = DayNutrition(
            date='2024-01-15',
            kcal=1800,
            protein=40,  # Below target
            fiber=10,    # Below target
            water_cups=4  # Below target
        )
        
        recommendations = service._get_daily_recommendations(low_protein_nutrition)
        
        assert len(recommendations) > 0
        assert any('protein' in rec.lower() for rec in recommendations)
        assert any('fiber' in rec.lower() or 'vegetables' in rec.lower() for rec in recommendations)
        assert any('water' in rec.lower() for rec in recommendations)

    def test_nutrition_strategies_database(self, service):
        """Test nutrition strategies are properly defined"""
        strategies = service.nutrition_strategies
        
        # Check required strategies exist
        required_strategies = [
            'intermittent_fasting',
            'time_restricted_eating', 
            'gut_health_focus',
            'plant_forward'
        ]
        
        for strategy in required_strategies:
            assert strategy in strategies
            assert 'name' in strategies[strategy]
            assert 'description' in strategies[strategy]
            assert 'benefits' in strategies[strategy]

    def test_parse_text_meal_plan_fallback(self, service):
        """Test fallback meal plan parsing"""
        mock_response = "Sample meal plan text that doesn't parse as JSON"
        
        result = service._parse_text_meal_plan(mock_response)
        
        assert isinstance(result, dict)
        assert 'days' in result
        assert 'monday' in result['days']
        assert 'parsing_note' in result

    def test_format_daily_summary(self, service, sample_nutrition_data):
        """Test daily nutrition summary formatting"""
        summary = service._format_daily_summary(sample_nutrition_data)
        
        assert '2024-01-15' in summary
        assert '1650 calories' in summary
        assert '85g protein' in summary
        assert '25g fiber' in summary
        assert '7 cups water' in summary
        assert '🙂' in summary  # Mood emoji

    def test_calculate_nutrition_trends_from_history(self, service):
        """Test nutrition trend calculation from history"""
        history = [
            DayNutrition(date='2024-01-13', kcal=1600, protein=80, fiber=20, water_cups=6),
            DayNutrition(date='2024-01-14', kcal=1700, protein=90, fiber=25, water_cups=7),
            DayNutrition(date='2024-01-15', kcal=1650, protein=85, fiber=23, water_cups=8)
        ]
        
        trends = service._calculate_nutrition_trends(history)
        
        assert trends['avg_calories'] == 1650  # (1600+1700+1650)/3
        assert trends['avg_protein'] == 85.0   # (80+90+85)/3
        assert 'trend_direction' in trends

    def test_format_weekly_summary(self, service):
        """Test weekly nutrition summary formatting"""
        history = [
            DayNutrition(date='2024-01-13', kcal=1600, protein=80, fiber=20, water_cups=6),
            DayNutrition(date='2024-01-14', kcal=1700, protein=90, fiber=25, water_cups=7)
        ]
        
        summary = service._format_weekly_summary(history)
        
        assert 'Weekly Summary' in summary
        assert '1650 cal' in summary  # Average calories
        assert '85.0g protein' in summary  # Average protein

    @patch('src.services.consolidated_ai_nutrition_service.aiohttp.ClientSession')
    async def test_enhanced_recipe_search(self, mock_session, service, sample_user_profile):
        """Test enhanced recipe search functionality"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'hits': [{
                'recipe': {
                    'label': 'Vegetarian Buddha Bowl',
                    'totalTime': 30,
                    'yield': 2,
                    'calories': 450,
                    'dietLabels': ['vegetarian'],
                    'healthLabels': ['tree-nut-free'],
                    'url': 'https://example.com/recipe',
                    'ingredients': []
                }
            }]
        })
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        result = await service.enhanced_recipe_search('buddha bowl', sample_user_profile)
        
        assert result['total_results'] == 1
        assert result['search_query'] == 'buddha bowl'
        assert 'recipes' in result
        assert len(result['recipes']) == 1
        
        recipe = result['recipes'][0]
        assert 'user_score' in recipe
        assert 'difficulty' in recipe
        assert recipe['label'] == 'Vegetarian Buddha Bowl'


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
