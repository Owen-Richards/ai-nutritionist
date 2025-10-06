"""
AI Service Integration Module
Unified interface for all AI operations with the enhanced services
"""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

from .enhanced_service import enhanced_ai_service
from .performance_monitor import ai_monitor
from .prompt_engine import prompt_engine
from ...config.ai_config import ai_config


class AIServiceIntegration:
    """
    Unified AI service interface with all enhancements
    """
    
    def __init__(self):
        self.ai_service = enhanced_ai_service
        self.monitor = ai_monitor
        self.prompt_engine = prompt_engine
        self.config = ai_config
    
    async def process_nutrition_request(self, request_type: str, user_input: Dict[str, Any],
                                      user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process any nutrition-related AI request with full optimization
        """
        try:
            # Generate AI response
            response = await self.ai_service.generate_nutrition_response(
                request_type=request_type,
                user_input=user_input,
                user_profile=user_profile
            )
            
            # Collect metrics for monitoring
            await self._update_request_metrics(request_type, response)
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': f"AI service error: {str(e)}",
                'fallback': True,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_meal_plan(self, preferences: Dict[str, Any], 
                          user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate optimized meal plan
        """
        meal_input = {
            'meal_type': preferences.get('meal_type', 'weekly'),
            'household_size': preferences.get('household_size', 1),
            'budget': preferences.get('budget', 75),
            'dietary_restrictions': preferences.get('dietary_restrictions', 'none'),
            'cuisine_preferences': preferences.get('cuisine_preferences', 'any'),
            'max_cooking_time': preferences.get('max_cooking_time', 45),
            'nutrition_goals': preferences.get('nutrition_goals', 'balanced')
        }
        
        return await self.process_nutrition_request('meal_planning', meal_input, user_profile)
    
    async def analyze_nutrition(self, food_item: str,
                              user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze nutrition content of food item
        """
        nutrition_input = {
            'food_item': food_item
        }
        
        return await self.process_nutrition_request('nutrition_analysis', nutrition_input, user_profile)
    
    async def suggest_recipe(self, ingredients: List[str], preferences: Dict[str, Any],
                           user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate recipe suggestions based on ingredients
        """
        recipe_input = {
            'ingredients': ', '.join(ingredients),
            'cooking_method': preferences.get('cooking_method', 'any'),
            'dietary_style': preferences.get('dietary_style', 'any'),
            'difficulty_level': preferences.get('difficulty_level', 'medium'),
            'max_prep_time': preferences.get('max_prep_time', 30)
        }
        
        return await self.process_nutrition_request('recipe_suggestion', recipe_input, user_profile)
    
    async def answer_nutrition_question(self, question: str,
                                      user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Answer general nutrition questions
        """
        question_input = {
            'question': question,
            'age': user_profile.get('age', 'adult') if user_profile else 'adult',
            'gender': user_profile.get('gender', 'unspecified') if user_profile else 'unspecified',
            'activity_level': user_profile.get('activity_level', 'moderate') if user_profile else 'moderate',
            'fitness_goal': user_profile.get('fitness_goal', 'maintenance') if user_profile else 'maintenance'
        }
        
        return await self.process_nutrition_request('nutrition_question', question_input, user_profile)
    
    async def find_ingredient_substitutes(self, ingredient: str, recipe_context: str,
                                        restrictions: List[str] = None,
                                        user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Find ingredient substitutions
        """
        substitute_input = {
            'ingredient': ingredient,
            'recipe_context': recipe_context,
            'restrictions': ', '.join(restrictions) if restrictions else 'none',
            'available_ingredients': 'common pantry items',
            'cooking_method': 'as specified in recipe'
        }
        
        return await self.process_nutrition_request('ingredient_substitute', substitute_input, user_profile)
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive AI performance dashboard
        """
        return await self.monitor.collect_real_time_metrics()
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate detailed performance report
        """
        return await self.monitor.generate_performance_report()
    
    def get_available_models(self) -> Dict[str, Any]:
        """
        Get information about available AI models
        """
        models_info = {}
        
        for model_enum, config in self.config.model_configs.items():
            models_info[model_enum.name] = {
                'model_id': config.model_id,
                'cost_per_1k_tokens': config.cost_per_1k_tokens,
                'quality_score': config.quality_score,
                'avg_response_time_ms': config.avg_response_time_ms,
                'use_cases': config.use_cases,
                'max_tokens': config.max_tokens
            }
        
        return models_info
    
    def optimize_configuration(self, user_tier: str = "free") -> Dict[str, Any]:
        """
        Get optimized configuration recommendations for user tier
        """
        recommendations = []
        
        if user_tier == "free":
            recommendations.extend([
                "Use Titan Text Express for general questions (cost-effective)",
                "Cache responses aggressively (24+ hours for stable content)",
                "Limit complex requests to essential use cases",
                "Use shorter prompts and reduce max_tokens where possible"
            ])
        elif user_tier == "premium":
            recommendations.extend([
                "Use Claude-3-Sonnet for complex meal planning",
                "Use Claude-3-Haiku for quick questions",
                "Enable all advanced features including creative recipe generation",
                "Optimize for quality over cost"
            ])
        else:  # standard
            recommendations.extend([
                "Use Claude-3-Haiku for most requests",
                "Use Claude-3-Sonnet for complex meal planning only",
                "Balance cache TTL (12-24 hours for most content)",
                "Moderate token limits for cost control"
            ])
        
        return {
            'user_tier': user_tier,
            'recommendations': recommendations,
            'suggested_models': self._get_suggested_models_for_tier(user_tier),
            'cache_strategy': self._get_cache_strategy_for_tier(user_tier)
        }
    
    def _get_suggested_models_for_tier(self, user_tier: str) -> Dict[str, str]:
        """Get suggested models for user tier"""
        if user_tier == "free":
            return {
                'primary': 'TITAN_TEXT_EXPRESS',
                'fallback': 'CLAUDE_3_HAIKU',
                'complex_tasks': 'CLAUDE_3_HAIKU'
            }
        elif user_tier == "premium":
            return {
                'primary': 'CLAUDE_3_SONNET',
                'fallback': 'CLAUDE_3_HAIKU',
                'complex_tasks': 'CLAUDE_3_OPUS'
            }
        else:  # standard
            return {
                'primary': 'CLAUDE_3_HAIKU',
                'fallback': 'TITAN_TEXT_EXPRESS',
                'complex_tasks': 'CLAUDE_3_SONNET'
            }
    
    def _get_cache_strategy_for_tier(self, user_tier: str) -> Dict[str, int]:
        """Get cache TTL strategy for user tier"""
        if user_tier == "free":
            return {
                'nutrition_analysis': 168,  # 7 days
                'recipe_suggestions': 48,   # 2 days
                'meal_plans': 24,          # 1 day
                'general_questions': 72    # 3 days
            }
        elif user_tier == "premium":
            return {
                'nutrition_analysis': 72,  # 3 days (fresher data)
                'recipe_suggestions': 24,  # 1 day (more variety)
                'meal_plans': 12,         # 12 hours (more personalized)
                'general_questions': 48   # 2 days
            }
        else:  # standard
            return {
                'nutrition_analysis': 120, # 5 days
                'recipe_suggestions': 36,  # 1.5 days
                'meal_plans': 18,         # 18 hours
                'general_questions': 60   # 2.5 days
            }
    
    async def _update_request_metrics(self, request_type: str, response: Dict[str, Any]) -> None:
        """Update request metrics for monitoring"""
        try:
            # This would typically update CloudWatch metrics
            # For now, we'll just log the request
            pass
        except Exception as e:
            # Don't let metrics collection fail the main request
            pass
    
    async def batch_process_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple AI requests in parallel for efficiency
        """
        tasks = []
        
        for request in requests:
            task = self.process_nutrition_request(
                request_type=request.get('type'),
                user_input=request.get('input', {}),
                user_profile=request.get('user_profile')
            )
            tasks.append(task)
        
        # Execute all requests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': f"Batch processing error: {str(result)}",
                    'request_index': i
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get overall AI service status
        """
        ai_metrics = self.ai_service.get_performance_metrics()
        
        return {
            'status': 'healthy' if ai_metrics.get('error_rate', 0) < 0.1 else 'degraded',
            'uptime': '99.9%',  # This would be calculated from actual uptime data
            'last_health_check': datetime.utcnow().isoformat(),
            'performance_summary': {
                'total_requests': ai_metrics.get('total_requests', 0),
                'success_rate': f"{(1 - ai_metrics.get('error_rate', 0)) * 100:.1f}%",
                'avg_response_time': f"{ai_metrics.get('avg_response_time', 0):.2f}s",
                'cache_hit_rate': f"{ai_metrics.get('cache_hit_rate', 0) * 100:.1f}%"
            },
            'active_models': list(ai_metrics.get('model_usage_distribution', {}).keys()),
            'circuit_breaker_status': ai_metrics.get('circuit_breaker_status', {}),
            'version': '2.0.0'
        }


# Global instance
ai_integration = AIServiceIntegration()
