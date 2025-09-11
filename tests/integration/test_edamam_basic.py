"""
Basic validation tests for Edamam integration
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_edamam_service_import():
    """Test that EdamamService can be imported"""
    from src.services.edamam_service import EdamamService
    assert EdamamService is not None


def test_enhanced_ai_service_import():
    """Test that enhanced AIService can be imported"""
    from src.services.ai_service import AIService
    assert AIService is not None


def test_recipe_difficulty_calculation():
    """Test recipe difficulty scoring without API calls"""
    from src.services.edamam_service import EdamamService
    from unittest.mock import patch
    
    with patch('boto3.resource'), patch('boto3.client'):
        service = EdamamService()
        
        # Test easy recipe
        easy_recipe = {
            'totalTime': 15,
            'ingredients': [
                {'text': '2 slices bread'},
                {'text': '1 tbsp butter'}
            ]
        }
        
        difficulty = service.calculate_recipe_difficulty(easy_recipe, 'beginner')
        assert 1 <= difficulty <= 5
        assert difficulty <= 3  # Should be easy
        
        # Test complex recipe
        complex_recipe = {
            'totalTime': 90,
            'ingredients': [
                {'text': 'marinate chicken for 2 hours'},
                {'text': 'julienne vegetables'},
                {'text': 'sauté until golden'},
            ] * 5  # 15 ingredients
        }
        
        difficulty = service.calculate_recipe_difficulty(complex_recipe, 'beginner')
        assert 1 <= difficulty <= 5
        assert difficulty >= 3  # Should be harder


def test_whatsapp_formatting():
    """Test WhatsApp recipe formatting"""
    from src.services.edamam_service import EdamamService
    from unittest.mock import patch
    
    with patch('boto3.resource'), patch('boto3.client'):
        service = EdamamService()
        
        recipe_data = {
            'label': 'Test Recipe',
            'totalTime': 20,
            'yield': 2,
            'calories': 350,
            'ingredients': [
                {'text': '1 cup quinoa'},
                {'text': '2 cups vegetables'}
            ],
            'shareAs': 'https://example.com/recipe'
        }
        
        formatted = service.format_recipe_for_whatsapp(recipe_data)
        
        # Check for emojis and key information
        assert '🍽️' in formatted
        assert '⏱️' in formatted
        assert 'Test Recipe' in formatted
        assert '20 mins' in formatted
        assert '350 calories' in formatted


def test_diet_label_extraction():
    """Test diet label extraction from user profile"""
    from src.services.edamam_service import EdamamService
    from unittest.mock import patch
    
    with patch('boto3.resource'), patch('boto3.client'):
        service = EdamamService()
        
        user_profile = {
            'dietary_restrictions': ['vegetarian', 'gluten-free', 'low-carb']
        }
        
        diet_labels = service._extract_diet_labels(user_profile)
        health_labels = service._extract_health_labels(user_profile)
        
        assert 'vegetarian' in diet_labels
        assert 'low-carb' in diet_labels
        assert 'gluten-free' in health_labels


def test_enhanced_nutrition_handler_classification():
    """Test message classification in enhanced handler"""
    from src.handlers.enhanced_nutrition_handler import EnhancedNutritionHandler
    from unittest.mock import patch
    
    # Mock all service dependencies
    with patch('src.handlers.enhanced_nutrition_handler.AIService'), \
         patch('src.handlers.enhanced_nutrition_handler.EdamamService'), \
         patch('src.handlers.enhanced_nutrition_handler.UserService'), \
         patch('src.handlers.enhanced_nutrition_handler.UniversalMessagingService'):
        
        handler = EnhancedNutritionHandler()
        
        # Test nutrition queries
        assert handler._is_nutrition_query('what are the calories in this meal?')
        assert handler._is_nutrition_query('show me nutritional information')
        
        # Test recipe requests
        assert handler._is_recipe_request('recipe for pasta')
        assert handler._is_recipe_request('how to cook chicken')
        
        # Test substitution requests
        assert handler._is_substitution_request('substitute for eggs')
        assert handler._is_substitution_request('dairy-free alternative')
        
        # Test meal plan requests
        assert handler._is_meal_plan_request('create meal plan')
        assert handler._is_meal_plan_request('what should I eat this week')


def test_ingredient_extraction():
    """Test ingredient extraction from messages"""
    from src.handlers.enhanced_nutrition_handler import EnhancedNutritionHandler
    from unittest.mock import patch
    
    with patch('src.handlers.enhanced_nutrition_handler.AIService'), \
         patch('src.handlers.enhanced_nutrition_handler.EdamamService'), \
         patch('src.handlers.enhanced_nutrition_handler.UserService'), \
         patch('src.handlers.enhanced_nutrition_handler.UniversalMessagingService'):
        
        handler = EnhancedNutritionHandler()
        
        message = "I have chicken, rice, and broccoli for dinner"
        ingredients = handler._extract_ingredients_from_message(message)
        
        assert 'chicken' in ingredients
        assert 'rice' in ingredients
        assert 'broccoli' in ingredients


if __name__ == '__main__':
    pytest.main(['-v', __file__])
