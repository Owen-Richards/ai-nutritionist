"""
Unit tests for AIService
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import os


# Mock AWS environment before importing our service
@patch.dict(os.environ, {
    'AWS_DEFAULT_REGION': 'us-east-1',
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
    'AWS_SECURITY_TOKEN': 'testing',
    'AWS_SESSION_TOKEN': 'testing'
})
@patch('boto3.client')
class TestAIService:
    """Test cases for AIService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('boto3.client'):
            from src.services.ai_service import AIService
            self.ai_service = AIService()
    
    def test_init(self, mock_boto_client):
        """Test AIService initialization"""
        from src.services.ai_service import AIService
        service = AIService()
        assert service.model_id == "amazon.titan-text-express-v1"
        mock_boto_client.assert_called_with('bedrock-runtime')
    
    def test_build_meal_plan_prompt(self):
        """Test meal plan prompt generation"""
        user_profile = {
            'dietary_restrictions': ['vegetarian'],
            'household_size': 2,
            'weekly_budget': 50,
            'fitness_goals': 'weight_loss',
            'allergies': ['nuts']
        }
        
        prompt = self.ai_service._build_meal_plan_prompt(user_profile)
        
        assert 'vegetarian' in prompt
        assert '2 people' in prompt
        assert '$50' in prompt
        assert 'weight_loss' in prompt
        assert 'nuts' in prompt
        assert 'JSON' in prompt
    
    def test_parse_meal_plan_response_valid_json(self):
        """Test parsing valid JSON meal plan response"""
        response = '''
        Here's your meal plan:
        {
            "days": [
                {
                    "day": "Monday",
                    "breakfast": "Oatmeal with berries",
                    "lunch": "Veggie wrap",
                    "dinner": "Pasta primavera"
                }
            ],
            "estimated_cost": 45,
            "nutrition_notes": "Balanced vegetarian plan"
        }
        '''
        
        result = self.ai_service._parse_meal_plan_response(response)
        
        assert result is not None
        assert 'days' in result
        assert len(result['days']) == 1
        assert result['days'][0]['day'] == 'Monday'
        assert result['estimated_cost'] == 45
    
    def test_parse_meal_plan_response_invalid_json(self):
        """Test parsing invalid JSON falls back to text parsing"""
        response = '''
        Monday:
        Breakfast: Oatmeal with berries
        Lunch: Veggie wrap
        Dinner: Pasta primavera
        
        Tuesday:
        Breakfast: Smoothie bowl
        '''
        
        result = self.ai_service._parse_meal_plan_response(response)
        
        assert result is not None
        assert 'days' in result
        assert len(result['days']) >= 1
    
    def test_parse_grocery_list_response(self):
        """Test grocery list parsing"""
        response = '''
        {
            "items": [
                {"name": "Bananas (6)", "category": "Produce"},
                {"name": "Oats (1 container)", "category": "Pantry"},
                {"name": "Almond milk (1 carton)", "category": "Dairy"}
            ]
        }
        '''
        
        result = self.ai_service._parse_grocery_list_response(response)
        
        assert len(result) == 3
        assert result[0]['name'] == 'Bananas (6)'
        assert result[0]['category'] == 'Produce'
    
    def test_build_nutrition_advice_prompt(self):
        """Test nutrition advice prompt building"""
        user_profile = {
            'dietary_restrictions': ['vegan'],
            'fitness_goals': 'muscle_gain'
        }
        question = "What are good protein sources?"
        
        prompt = self.ai_service._build_nutrition_advice_prompt(question, user_profile)
        
        assert 'vegan' in prompt
        assert 'muscle_gain' in prompt
        assert question in prompt
        assert 'nutritionist' in prompt.lower()
    
    @patch('boto3.client')
    def test_invoke_model_success(self, mock_boto_client):
        """Test successful model invocation"""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'results': [{'outputText': 'Test response'}]
        }).encode()
        
        mock_client = Mock()
        mock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_client
        
        service = AIService()
        result = service._invoke_model("Test prompt")
        
        assert result == "Test response"
        mock_client.invoke_model.assert_called_once()
    
    @patch('boto3.client')
    def test_invoke_model_failure(self, mock_boto_client):
        """Test model invocation failure handling"""
        mock_client = Mock()
        mock_client.invoke_model.side_effect = Exception("API Error")
        mock_boto_client.return_value = mock_client
        
        service = AIService()
        result = service._invoke_model("Test prompt")
        
        assert result is None
    
    def test_parse_text_grocery_list(self):
        """Test parsing text-based grocery lists"""
        response = '''
        Produce:
        • Bananas (6)
        • Spinach (1 bag)
        
        Pantry:
        - Oats (1 container)
        - Rice (2 lbs)
        '''
        
        result = self.ai_service._parse_text_grocery_list(response)
        
        assert len(result) >= 4
        # Check that items are properly categorized
        produce_items = [item for item in result if item['category'] == 'Produce']
        pantry_items = [item for item in result if item['category'] == 'Pantry']
        
        assert len(produce_items) == 2
        assert len(pantry_items) == 2
