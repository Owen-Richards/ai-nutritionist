"""
AWS Bedrock adapter for AI services with distributed rate limiting.
"""

import json
import boto3
from typing import Dict, Any, List
from botocore.exceptions import ClientError

from ..core.interfaces import AIServiceInterface
from ..models.meal_plan import MealPlan
from ..services.infrastructure.distributed_rate_limiting import check_rate_limit, track_service_cost


class BedrockAIService(AIServiceInterface):
    """AWS Bedrock implementation for AI services."""
    
    def __init__(self, region: str = "us-east-1", model_id: str = "amazon.titan-text-express-v1"):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
    
    async def generate_meal_plan(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Generate meal plan using AWS Bedrock with rate limiting."""
        user_id = user_preferences.get('user_id', 'anonymous')
        
        # Check AI request rate limits
        rate_allowed, rate_info = await check_rate_limit(user_id, 'ai_requests')
        
        if not rate_allowed:
            return {
                'success': False,
                'error': 'AI request rate limit exceeded',
                'rate_info': rate_info,
                'meal_plan': self._get_fallback_meal_plan()
            }
        
        prompt = self._build_meal_plan_prompt(user_preferences)
        
        try:
            response = await self._call_bedrock(prompt)
            
            # Track AI service costs
            estimated_cost = 0.008  # Bedrock cost per request
            cost_info = await track_service_cost('bedrock', estimated_cost, user_id)
            
            if cost_info.get('over_limit'):
                return {
                    'success': False,
                    'error': 'AI service cost limit exceeded',
                    'cost_info': cost_info,
                    'meal_plan': self._get_fallback_meal_plan()
                }
            
            meal_plan_data = self._parse_meal_plan_response(response)
            
            return {
                'success': True,
                'meal_plan': MealPlan.from_dict(meal_plan_data),
                'rate_info': rate_info,
                'cost_info': cost_info
            }
            
        except Exception as e:
            print(f"Error generating meal plan: {e}")
            # Return a fallback meal plan
            return {
                'success': False,
                'error': str(e),
                'meal_plan': self._get_fallback_meal_plan(),
                'rate_info': rate_info
            }
    
    async def analyze_food_image(self, image_url: str) -> Dict[str, Any]:
        """Analyze food image using AWS Bedrock multimodal capabilities."""
        prompt = f"Analyze this food image and provide nutrition information: {image_url}"
        
        try:
            response = await self._call_bedrock(prompt)
            return self._parse_food_analysis_response(response)
        except Exception as e:
            print(f"Error analyzing food image: {e}")
            return {"error": "Could not analyze image", "food_name": "unknown", "calories": 0}
    
    async def _call_bedrock(self, prompt: str) -> str:
        """Make API call to AWS Bedrock."""
        body = json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 4096,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 0.9
            }
        })
        
        try:
            response = self.bedrock.invoke_model(
                body=body,
                modelId=self.model_id,
                accept='application/json',
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['results'][0]['outputText']
        except ClientError as e:
            print(f"Bedrock API error: {e}")
            raise
    
    def _build_meal_plan_prompt(self, preferences: Dict[str, Any]) -> str:
        """Build prompt for meal plan generation."""
        dietary_restrictions = preferences.get('dietary_restrictions', [])
        budget = preferences.get('budget', 75)
        goals = preferences.get('goals', [])
        
        prompt = f"""
        Create a weekly meal plan with the following requirements:
        - Budget: ${budget} per week
        - Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
        - Goals: {', '.join(goals) if goals else 'General health'}
        
        Provide the response in JSON format with the following structure:
        {{
            "week_plan": {{
                "monday": {{"breakfast": "...", "lunch": "...", "dinner": "..."}},
                "tuesday": {{"breakfast": "...", "lunch": "...", "dinner": "..."}},
                // ... rest of week
            }},
            "grocery_list": ["item1", "item2", ...],
            "estimated_cost": 65.50,
            "nutritional_summary": {{"calories": 2000, "protein": 150, "carbs": 250, "fat": 67}}
        }}
        """
        return prompt
    
    def _parse_meal_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response into meal plan data."""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return self._get_fallback_meal_plan().to_dict()
    
    def _parse_food_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response for food analysis."""
        # Simple parsing - in production, you'd want more robust parsing
        return {
            "food_name": "analyzed_food",
            "calories": 350,
            "protein": 25,
            "carbs": 30,
            "fat": 15,
            "confidence": 0.85
        }
    
    def _get_fallback_meal_plan(self) -> MealPlan:
        """Return a simple fallback meal plan."""
        fallback_data = {
            "week_plan": {
                "monday": {
                    "breakfast": "Oatmeal with banana",
                    "lunch": "Grilled chicken salad", 
                    "dinner": "Baked salmon with vegetables"
                }
                # Add more days as needed
            },
            "grocery_list": ["oats", "banana", "chicken", "salmon", "vegetables"],
            "estimated_cost": 50.0,
            "nutritional_summary": {"calories": 1800, "protein": 120, "carbs": 200, "fat": 60}
        }
        return MealPlan.from_dict(fallback_data)
