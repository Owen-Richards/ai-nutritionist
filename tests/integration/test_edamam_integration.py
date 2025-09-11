"""
Test suite for Enhanced Edamam API Integration
Tests the optimization features and cost management
"""

import pytest
import asyncio
import json
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.edamam_service import EdamamService, EdamamUsageTracker
from src.services.ai_service import AIService
from src.handlers.enhanced_nutrition_handler import EnhancedNutritionHandler


class TestEdamamService:
    """Test the enhanced Edamam service functionality"""
    
    @pytest.fixture
    def edamam_service(self):
        """Create Edamam service instance for testing"""
        with patch('boto3.resource'), patch('boto3.client'):
            service = EdamamService()
            # Mock API credentials
            service.recipe_api_key = 'test_key'
            service.recipe_app_id = 'test_app_id'
            service.nutrition_api_key = 'test_nutrition_key'
            service.nutrition_app_id = 'test_nutrition_app_id'
            return service
    
    @pytest.fixture
    def user_profile(self):
        """Sample user profile for testing"""
        return {
            'user_id': 'test_user_123',
            'dietary_restrictions': ['vegetarian', 'gluten-free'],
            'max_prep_time': 30,
            'min_calories': 300,
            'max_calories': 600,
            'daily_calories': 2000,
            'fitness_goal': 'weight_loss',
            'cooking_skill': 'intermediate'
        }
    
    @pytest.mark.asyncio
    async def test_enhanced_recipe_search(self, edamam_service, user_profile):
        """Test enhanced recipe search with caching"""
        
        # Mock API response
        mock_response = {
            'hits': [
                {
                    'recipe': {
                        'label': 'Vegetarian Pasta',
                        'url': 'https://example.com/recipe',
                        'image': 'https://example.com/image.jpg',
                        'totalTime': 25,
                        'yield': 4,
                        'calories': 480,
                        'ingredients': [
                            {'text': '2 cups pasta'},
                            {'text': '1 cup vegetables'}
                        ],
                        'dietLabels': ['Vegetarian'],
                        'healthLabels': ['Gluten-Free']
                    }
                }
            ]
        }
        
        with patch.object(edamam_service, '_make_edamam_request', 
                         new_callable=AsyncMock, return_value=mock_response):
            with patch.object(edamam_service, '_get_from_cache', 
                             new_callable=AsyncMock, return_value=None):
                with patch.object(edamam_service, '_cache_result', 
                                 new_callable=AsyncMock):
                    with patch.object(edamam_service, '_log_api_usage', 
                                     new_callable=AsyncMock):
                        
                        result = await edamam_service.enhanced_recipe_search(
                            'pasta', user_profile
                        )
                        
                        assert 'recipes' in result
                        assert len(result['recipes']) == 1
                        assert result['recipes'][0]['label'] == 'Vegetarian Pasta'
                        assert result['recipes'][0]['difficulty'] is not None
    
    @pytest.mark.asyncio 
    async def test_nutrition_analysis(self, edamam_service):
        """Test nutrition analysis functionality"""
        
        ingredients = ['1 cup rice', '100g chicken breast', '1 tbsp olive oil']
        
        mock_nutrition_response = {
            'calories': 450,
            'totalWeight': 300,
            'totalNutrients': {
                'PROCNT': {'quantity': 25},
                'CHOCDF': {'quantity': 60},
                'FAT': {'quantity': 15},
                'FIBTG': {'quantity': 2}
            },
            'totalDaily': {
                'PROCNT': {'quantity': 50},
                'VITC': {'quantity': 25}
            }
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_nutrition_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            with patch.object(edamam_service, '_get_from_cache', 
                             new_callable=AsyncMock, return_value=None):
                with patch.object(edamam_service, '_cache_result', 
                                 new_callable=AsyncMock):
                    with patch.object(edamam_service, '_check_usage_limits', 
                                     new_callable=AsyncMock, return_value=True):
                        
                        result = await edamam_service.analyze_meal_nutrition(
                            ingredients, 'test_user'
                        )
                        
                        assert 'calories' in result
                        assert result['calories'] == 450
                        assert 'macros' in result
                        assert result['macros']['protein'] == 25
    
    @pytest.mark.asyncio
    async def test_ingredient_validation(self, edamam_service):
        """Test ingredient validation and parsing"""
        
        mock_food_db_response = {
            'parsed': [
                {
                    'food': {
                        'label': 'Chicken Breast',
                        'nutrients': {
                            'ENERC_KCAL': 165,
                            'PROCNT': 31,
                            'CHOCDF': 0
                        }
                    }
                }
            ],
            'hints': [
                {
                    'food': {
                        'label': 'Chicken Thigh',
                        'category': 'Generic foods',
                        'nutrients': {'ENERC_KCAL': 250}
                    }
                }
            ]
        }
        
        with patch.object(edamam_service, '_make_edamam_request', 
                         new_callable=AsyncMock, return_value=mock_food_db_response):
            with patch.object(edamam_service, '_get_from_cache', 
                             new_callable=AsyncMock, return_value=None):
                
                result = await edamam_service.validate_ingredients('chicken breast')
                
                assert 'parsed_ingredients' in result
                assert len(result['parsed_ingredients']) == 1
                assert result['parsed_ingredients'][0]['label'] == 'Chicken Breast'
                assert result['parsed_ingredients'][0]['known'] == True
    
    def test_recipe_difficulty_calculation(self, edamam_service):
        """Test recipe difficulty scoring algorithm"""
        
        # Easy recipe
        easy_recipe = {
            'totalTime': 15,
            'ingredients': [
                {'text': '2 slices bread'},
                {'text': '1 tbsp butter'}
            ]
        }
        
        difficulty = edamam_service.calculate_recipe_difficulty(
            easy_recipe, 'beginner'
        )
        assert difficulty <= 2
        
        # Complex recipe  
        complex_recipe = {
            'totalTime': 90,
            'ingredients': [
                {'text': 'marinate chicken for 2 hours'},
                {'text': 'julienne vegetables'},
                {'text': 'sauté until golden'},
                {'text': 'emulsify the sauce'},
                {'text': 'fold in cream slowly'}
            ] * 3  # 15 ingredients
        }
        
        difficulty = edamam_service.calculate_recipe_difficulty(
            complex_recipe, 'beginner'
        )
        assert difficulty >= 4
    
    def test_whatsapp_formatting(self, edamam_service):
        """Test WhatsApp-optimized recipe formatting"""
        
        recipe_data = {
            'label': 'Healthy Quinoa Salad',
            'totalTime': 20,
            'yield': 2,
            'calories': 350,
            'ingredients': [
                {'text': '1 cup quinoa'},
                {'text': '2 cups mixed vegetables'},
                {'text': '1 tbsp olive oil'}
            ],
            'shareAs': 'https://example.com/recipe'
        }
        
        formatted = edamam_service.format_recipe_for_whatsapp(recipe_data)
        
        assert '🍽️' in formatted  # Food emoji
        assert '⏱️' in formatted  # Clock emoji
        assert '👥' in formatted  # People emoji
        assert '🔥' in formatted  # Fire emoji (calories)
        assert 'Healthy Quinoa Salad' in formatted
        assert '20 mins' in formatted
        assert '350 calories' in formatted
        assert 'nutrition' in formatted.lower()
    
    @pytest.mark.asyncio
    async def test_substitution_suggestions(self, edamam_service):
        """Test ingredient substitution logic"""
        
        # Test dairy-free substitutions
        substitutions = await edamam_service.suggest_substitutions(
            'milk', ['dairy-free']
        )
        
        assert len(substitutions) > 0
        assert any('almond milk' in sub.lower() or 'oat milk' in sub.lower() 
                  for sub in substitutions)
        
        # Test gluten-free substitutions
        substitutions = await edamam_service.suggest_substitutions(
            'flour', ['gluten-free']
        )
        
        assert len(substitutions) > 0
        assert any('almond flour' in sub.lower() or 'rice flour' in sub.lower() 
                  for sub in substitutions)


class TestEdamamUsageTracker:
    """Test usage tracking and cost management"""
    
    @pytest.fixture
    def usage_tracker(self):
        """Create usage tracker instance for testing"""
        with patch('boto3.resource'):
            return EdamamUsageTracker()
    
    @pytest.mark.asyncio
    async def test_usage_limit_checking(self, usage_tracker):
        """Test API usage limit enforcement"""
        
        # Mock DynamoDB response for usage check
        with patch.object(usage_tracker.usage_table, 'get_item') as mock_get:
            # Test under limit
            mock_get.return_value = {'Item': {'count': 5}}
            
            edamam_service = EdamamService()
            result = await edamam_service._check_usage_limits('test_user', 'recipe_search')
            assert result == True  # Under limit of 50
            
            # Test over limit
            mock_get.return_value = {'Item': {'count': 55}}
            result = await edamam_service._check_usage_limits('test_user', 'recipe_search')
            assert result == False  # Over limit
    
    @pytest.mark.asyncio
    async def test_cost_tracking(self, usage_tracker):
        """Test API cost tracking functionality"""
        
        with patch.object(usage_tracker.usage_table, 'update_item') as mock_update:
            edamam_service = EdamamService()
            
            await edamam_service._log_api_usage('recipe_search', 0.002, 'test_user')
            
            # Verify that both system and user usage were logged
            assert mock_update.call_count == 2
            
            # Check system usage call
            system_call = mock_update.call_args_list[0]
            assert 'system#recipe_search#' in str(system_call)
            
            # Check user usage call
            user_call = mock_update.call_args_list[1]
            assert 'test_user#recipe_search#' in str(user_call)


class TestEnhancedNutritionHandler:
    """Test the enhanced nutrition message handler"""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing"""
        with patch('src.handlers.enhanced_nutrition_handler.AIService'), \
             patch('src.handlers.enhanced_nutrition_handler.EdamamService'), \
             patch('src.handlers.enhanced_nutrition_handler.UserService'), \
             patch('src.handlers.enhanced_nutrition_handler.MessagingService'):
            return EnhancedNutritionHandler()
    
    @pytest.fixture
    def user_profile(self):
        """Sample user profile for testing"""
        return {
            'user_id': 'test_user',
            'dietary_restrictions': ['vegetarian'],
            'daily_calories': 2000,
            'fitness_goal': 'maintenance'
        }
    
    def test_message_classification(self, handler):
        """Test message type classification"""
        
        # Test nutrition queries
        assert handler._is_nutrition_query('what are the calories in this meal?')
        assert handler._is_nutrition_query('show me the nutritional information')
        assert handler._is_nutrition_query('how much protein is in eggs?')
        
        # Test recipe requests
        assert handler._is_recipe_request('can you give me a recipe for pasta?')
        assert handler._is_recipe_request('how do I cook chicken breast?')
        assert handler._is_recipe_request('show me cooking instructions')
        
        # Test substitution requests
        assert handler._is_substitution_request('what can I use instead of eggs?')
        assert handler._is_substitution_request('dairy-free alternative to milk')
        assert handler._is_substitution_request('substitute for butter')
        
        # Test meal plan requests
        assert handler._is_meal_plan_request('create a meal plan for me')
        assert handler._is_meal_plan_request('what should I eat this week?')
        assert handler._is_meal_plan_request('plan my meals')
    
    def test_ingredient_extraction(self, handler):
        """Test ingredient extraction from messages"""
        
        message = "I have chicken, rice, and broccoli. What's the nutrition?"
        ingredients = handler._extract_ingredients_from_message(message)
        
        assert 'chicken' in ingredients
        assert 'rice' in ingredients
        assert 'broccoli' in ingredients
    
    def test_meal_name_extraction(self, handler):
        """Test meal name extraction from recipe requests"""
        
        # Test various patterns
        assert handler._extract_meal_name_from_message(
            "show me a recipe for chicken stir fry"
        ) == "chicken stir fry"
        
        assert handler._extract_meal_name_from_message(
            "how to make chocolate cake?"
        ) == "chocolate cake"
        
        assert handler._extract_meal_name_from_message(
            "can you help me cook salmon teriyaki"
        ) == "salmon teriyaki"
    
    @pytest.mark.asyncio
    async def test_nutrition_query_handling(self, handler, user_profile):
        """Test nutrition query handling with mock responses"""
        
        # Mock the AI service response
        mock_nutrition_result = {
            'success': True,
            'whatsapp_summary': '📊 **Nutrition Analysis**\n🔥 Calories: 450\n💪 Protein: 25g',
            'nutrition_data': {'calories': 450, 'macros': {'protein': 25}},
            'recommendations': ['Add more vegetables', 'Good protein content']
        }
        
        handler.ai_service.get_enhanced_nutrition_analysis = AsyncMock(
            return_value=mock_nutrition_result
        )
        
        result = await handler._handle_nutrition_query(
            'analyze the nutrition of chicken and rice', user_profile, 'whatsapp'
        )
        
        assert result['type'] == 'nutrition_analysis'
        assert '📊' in result['response']
        assert 'recommendations' in result['response'].lower()
    
    @pytest.mark.asyncio
    async def test_recipe_request_handling(self, handler, user_profile):
        """Test recipe request handling"""
        
        # Mock Edamam service response
        mock_recipe_results = {
            'recipes': [
                {
                    'label': 'Chicken Stir Fry',
                    'totalTime': 20,
                    'yield': 2,
                    'calories': 400,
                    'url': 'https://example.com/recipe'
                }
            ]
        }
        
        handler.edamam_service.enhanced_recipe_search = AsyncMock(
            return_value=mock_recipe_results
        )
        handler.edamam_service.format_recipe_for_whatsapp = Mock(
            return_value='🍽️ **Chicken Stir Fry**\n⏱️ 20 mins'
        )
        
        result = await handler._handle_recipe_request(
            'show me a recipe for chicken stir fry', user_profile, 'whatsapp'
        )
        
        assert result['type'] == 'recipe_search'
        assert 'Recipe Options' in result['response']
        assert 'Option 1' in result['response']


class TestIntegrationAndPerformance:
    """Integration tests and performance validation"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_meal_plan_generation(self):
        """Test complete meal plan generation with Edamam integration"""
        
        # This would be a more comprehensive test in practice
        user_profile = {
            'user_id': 'integration_test_user',
            'dietary_restrictions': ['vegetarian'],
            'budget': 50,
            'household_size': 2,
            'daily_calories': 1800
        }
        
        with patch('boto3.resource'), patch('boto3.client'):
            ai_service = AIService()
            
            # Mock the meal plan generation
            mock_meal_plan = {
                'days': {
                    'monday': {
                        'breakfast': {'name': 'Oatmeal with berries'},
                        'lunch': {'name': 'Quinoa salad'},
                        'dinner': {'name': 'Vegetable pasta'}
                    }
                },
                'weekly_budget': 50,
                'household_size': 2
            }
            
            ai_service._invoke_model_with_cache = Mock(return_value='Mock AI response')
            ai_service._parse_meal_plan_response = Mock(return_value=mock_meal_plan)
            
            # Test that the integration doesn't break
            meal_plan = ai_service.generate_meal_plan(user_profile)
            assert meal_plan is not None
            assert 'days' in meal_plan
    
    def test_cost_optimization_features(self):
        """Test that cost optimization features are properly implemented"""
        
        with patch('boto3.resource'), patch('boto3.client'):
            edamam_service = EdamamService()
            
            # Test that caching is implemented
            assert hasattr(edamam_service, '_get_from_cache')
            assert hasattr(edamam_service, '_cache_result')
            
            # Test that usage tracking is implemented
            assert hasattr(edamam_service, '_check_usage_limits')
            assert hasattr(edamam_service, '_log_api_usage')
            
            # Test that different cache TTLs are used for different API types
            # This would be tested by checking the actual cache calls
    
    def test_whatsapp_optimization(self):
        """Test WhatsApp-specific optimizations"""
        
        with patch('boto3.resource'), patch('boto3.client'):
            edamam_service = EdamamService()
            
            # Test recipe formatting
            recipe_data = {
                'label': 'Test Recipe',
                'totalTime': 30,
                'yield': 4,
                'calories': 500,
                'ingredients': [{'text': '1 cup test ingredient'}],
                'shareAs': 'https://example.com'
            }
            
            formatted = edamam_service.format_recipe_for_whatsapp(recipe_data)
            
            # Check for WhatsApp-friendly formatting
            assert len(formatted) < 4096  # WhatsApp message limit
            assert formatted.count('\n') < 20  # Reasonable line count
            assert any(emoji in formatted for emoji in ['🍽️', '⏱️', '👥', '🔥'])


if __name__ == '__main__':
    pytest.main(['-v', __file__])
