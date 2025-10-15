"""
AWS service implementations of external service interfaces
Infrastructure layer - separated from domain logic
"""

import json
import logging
import hashlib
import aiohttp
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from packages.core.src.interfaces.services import (
    NutritionAPIService,
    AIService,
    ConfigurationService,
    MonitoringService,
    AnalyticsService
)

logger = logging.getLogger(__name__)


class EdamamAPIService(NutritionAPIService):
    """Edamam API implementation of NutritionAPIService"""
    
    def __init__(self, config_service: ConfigurationService):
        self.config = config_service
        self.recipe_search_url = "https://api.edamam.com/api/recipes/v2"
        self.nutrition_analysis_url = "https://api.edamam.com/api/nutrition-details"
        self.food_database_url = "https://api.edamam.com/api/food-database/v2/parser"
    
    async def search_recipes(self, query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search for recipes with dietary filters"""
        try:
            # Get API credentials from config service
            api_key = await self.config.get_secret('/ai-nutritionist/edamam/recipe-api-key')
            app_id = await self.config.get_secret('/ai-nutritionist/edamam/recipe-app-id')
            
            if not api_key or not app_id:
                logger.error("Missing Edamam API credentials")
                return {}
            
            # Build search parameters
            params = {
                'type': 'public',
                'q': query,
                'app_id': app_id,
                'app_key': api_key,
                'from': filters.get('from', 0),
                'to': filters.get('to', 5),
                'random': 'true',
                'imageSize': 'SMALL'
            }
            
            # Add dietary filters
            if 'dietary_restrictions' in filters:
                params['diet'] = filters['dietary_restrictions']
            if 'health_labels' in filters:
                params['health'] = filters['health_labels']
            if 'max_prep_time' in filters:
                params['time'] = f"1-{filters['max_prep_time']}"
            if 'calorie_range' in filters:
                params['calories'] = filters['calorie_range']
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.recipe_search_url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Edamam API error: {response.status}")
                        return {}
        
        except Exception as e:
            logger.error(f"Error searching recipes: {e}")
            return {}
    
    async def analyze_nutrition(self, ingredients: List[str]) -> Dict[str, Any]:
        """Analyze nutritional content of ingredients"""
        try:
            api_key = await self.config.get_secret('/ai-nutritionist/edamam/nutrition-api-key')
            app_id = await self.config.get_secret('/ai-nutritionist/edamam/nutrition-app-id')
            
            if not api_key or not app_id:
                return {}
            
            headers = {'Content-Type': 'application/json'}
            params = {'app_id': app_id, 'app_key': api_key}
            payload = {'ingr': ingredients}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.nutrition_analysis_url,
                    params=params,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Nutrition analysis error: {response.status}")
                        return {}
        
        except Exception as e:
            logger.error(f"Error analyzing nutrition: {e}")
            return {}
    
    async def get_food_database_info(self, food_query: str) -> Dict[str, Any]:
        """Get food database information"""
        try:
            api_key = await self.config.get_secret('/ai-nutritionist/edamam/food-db-api-key')
            app_id = await self.config.get_secret('/ai-nutritionist/edamam/food-db-app-id')
            
            if not api_key or not app_id:
                return {}
            
            params = {
                'app_id': app_id,
                'app_key': api_key,
                'ingr': food_query,
                'nutrition-type': 'cooking'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.food_database_url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Food database error: {response.status}")
                        return {}
        
        except Exception as e:
            logger.error(f"Error getting food database info: {e}")
            return {}


class BedrockAIService(AIService):
    """AWS Bedrock implementation of AIService"""
    
    def __init__(self, config_service: ConfigurationService):
        self.config = config_service
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.model_id = "amazon.titan-text-express-v1"
    
    async def generate_meal_plan(self, user_preferences: Dict[str, Any], context: str) -> str:
        """Generate personalized meal plan"""
        try:
            prompt = self._build_meal_plan_prompt(user_preferences, context)
            
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            })
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body.get('results', [{}])[0].get('outputText', '')
        
        except Exception as e:
            logger.error(f"Error generating meal plan: {e}")
            return "Sorry, I'm having trouble generating a meal plan right now."
    
    async def generate_nutrition_advice(self, query: str, user_context: Dict[str, Any]) -> str:
        """Generate nutrition advice response"""
        try:
            prompt = self._build_nutrition_advice_prompt(query, user_context)
            
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 500,
                    "temperature": 0.6,
                    "topP": 0.8
                }
            })
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body.get('results', [{}])[0].get('outputText', '')
        
        except Exception as e:
            logger.error(f"Error generating nutrition advice: {e}")
            return "Sorry, I'm having trouble providing nutrition advice right now."
    
    async def analyze_dietary_patterns(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user dietary patterns"""
        try:
            # Implementation would analyze patterns using AI
            # For now, return basic analysis
            return {
                'dominant_patterns': [],
                'recommendations': [],
                'risk_factors': [],
                'positive_trends': []
            }
        except Exception as e:
            logger.error(f"Error analyzing dietary patterns: {e}")
            return {}
    
    def _build_meal_plan_prompt(self, preferences: Dict[str, Any], context: str) -> str:
        """Build prompt for meal plan generation"""
        return f"""
You are a professional nutritionist. Create a personalized meal plan based on these preferences:

Dietary Restrictions: {preferences.get('dietary_restrictions', [])}
Health Goals: {preferences.get('health_goals', [])}
Allergies: {preferences.get('allergies', [])}
Dislikes: {preferences.get('dislikes', [])}
Max Prep Time: {preferences.get('max_prep_time', 45)} minutes
Calorie Target: {preferences.get('calorie_target', 'Not specified')}

Context: {context}

Please provide a balanced meal plan with recipes that meet these requirements.
"""
    
    def _build_nutrition_advice_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build prompt for nutrition advice"""
        return f"""
You are a certified nutritionist. Answer this nutrition question professionally:

Question: {query}

User Context:
- Health Goals: {context.get('health_goals', [])}
- Dietary Restrictions: {context.get('dietary_restrictions', [])}
- Current Tier: {context.get('user_tier', 'free')}

Provide helpful, evidence-based nutrition advice.
"""


class AWSConfigurationService(ConfigurationService):
    """AWS Systems Manager Parameter Store implementation"""
    
    def __init__(self):
        self.ssm = boto3.client('ssm')
        self.secrets_cache = {}  # Simple in-memory cache
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret value from Parameter Store"""
        try:
            # Check cache first
            if secret_name in self.secrets_cache:
                return self.secrets_cache[secret_name]
            
            response = self.ssm.get_parameter(Name=secret_name, WithDecryption=True)
            value = response['Parameter']['Value']
            
            # Cache the value
            self.secrets_cache[secret_name] = value
            return value
        
        except ClientError as e:
            logger.error(f"Error getting secret {secret_name}: {e}")
            return None
    
    async def get_config(self, config_key: str, default: Any = None) -> Any:
        """Get configuration value"""
        try:
            response = self.ssm.get_parameter(Name=config_key)
            return response['Parameter']['Value']
        except ClientError:
            return default


class CloudWatchMonitoringService(MonitoringService):
    """AWS CloudWatch implementation of MonitoringService"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
    
    async def track_metric(self, metric_name: str, value: float, dimensions: Dict[str, str] = None) -> bool:
        """Track custom metric"""
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace='AINutritionist',
                MetricData=[metric_data]
            )
            return True
        
        except ClientError as e:
            logger.error(f"Error tracking metric {metric_name}: {e}")
            return False
    
    async def log_event(self, event_name: str, data: Dict[str, Any]) -> bool:
        """Log structured event"""
        try:
            # Implementation would send to CloudWatch Logs
            logger.info(f"Event: {event_name}", extra=data)
            return True
        except Exception as e:
            logger.error(f"Error logging event {event_name}: {e}")
            return False
    
    async def create_alarm(self, alarm_config: Dict[str, Any]) -> bool:
        """Create monitoring alarm"""
        try:
            self.cloudwatch.put_metric_alarm(**alarm_config)
            return True
        except ClientError as e:
            logger.error(f"Error creating alarm: {e}")
            return False


class CloudWatchAnalyticsService(AnalyticsService):
    """CloudWatch-based analytics implementation"""
    
    def __init__(self, monitoring_service: MonitoringService):
        self.monitoring = monitoring_service
        self.cloudwatch = boto3.client('cloudwatch')
    
    async def track_user_event(self, user_id: str, event: str, properties: Dict[str, Any]) -> bool:
        """Track user behavior event"""
        try:
            await self.monitoring.track_metric(
                metric_name=f"UserEvent.{event}",
                value=1.0,
                dimensions={'UserId': user_id}
            )
            
            await self.monitoring.log_event(f"user_event_{event}", {
                'user_id': user_id,
                'event': event,
                'properties': properties,
                'timestamp': datetime.utcnow().isoformat()
            })
            return True
        
        except Exception as e:
            logger.error(f"Error tracking user event: {e}")
            return False
    
    async def generate_report(self, report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics report"""
        try:
            # Implementation would query CloudWatch metrics and logs
            # For now, return basic structure
            return {
                'report_type': report_type,
                'generated_at': datetime.utcnow().isoformat(),
                'data': {},
                'parameters': parameters
            }
        except Exception as e:
            logger.error(f"Error generating report {report_type}: {e}")
            return {}
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get user behavior insights"""
        try:
            # Implementation would analyze user metrics
            return {
                'user_id': user_id,
                'insights': [],
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting user insights: {e}")
            return {}
