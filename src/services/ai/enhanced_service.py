"""
Enhanced AI Service with Advanced Performance Optimization
Multi-model support, intelligent fallbacks, and comprehensive caching
"""

import json
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import logging

from ...config.ai_config import ai_config, AIModel
from .prompt_engine import prompt_engine
from ..infrastructure.caching import AdvancedCachingService

logger = logging.getLogger(__name__)


class EnhancedAIService:
    """
    Enhanced AI service with multi-model support and advanced optimization
    """
    
    def __init__(self, region: str = "us-east-1"):
        # Initialize AWS clients with error handling for testing
        try:
            self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client: {e}")
            self.bedrock_runtime = None
        
        try:
            self.caching_service = AdvancedCachingService()
        except Exception as e:
            logger.warning(f"Failed to initialize caching service: {e}")
            self.caching_service = None
        
        # Performance tracking
        self.performance_metrics = {
            'requests_total': 0,
            'requests_cached': 0,
            'requests_failed': 0,
            'total_tokens_used': 0,
            'total_cost': 0.0,
            'avg_response_time': 0.0,
            'model_usage': {}
        }
        
        # Circuit breaker for model failures
        self.circuit_breakers = {}
        
        # Request queue for batch processing
        self.request_queue = []
        self.batch_processing_enabled = True
    
    async def generate_nutrition_response(self, request_type: str, user_input: Dict[str, Any], 
                                        user_profile: Optional[Dict[str, Any]] = None,
                                        priority: str = "normal") -> Dict[str, Any]:
        """
        Generate AI response with intelligent model selection and optimization
        """
        start_time = time.time()
        
        try:
            # Select optimal template and model
            template_name = self._map_request_to_template(request_type)
            model_config = ai_config.select_optimal_model(
                use_case=request_type,
                user_tier=user_profile.get('tier', 'free') if user_profile else 'free',
                complexity_score=self._assess_complexity(user_input)
            )
            
            # Build optimized prompt
            prompt, template = prompt_engine.build_optimized_prompt(
                template_name, user_input, {'user_profile': user_profile}
            )
            
            # Generate cache key
            cache_key = prompt_engine.generate_cache_key(template_name, user_input)
            
            # Check cache first
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                self.performance_metrics['requests_cached'] += 1
                return self._format_response(cached_response, cached=True, response_time=time.time() - start_time)
            
            # Optimize prompt for selected model
            optimized_prompt = prompt_engine.optimize_prompt_for_model(prompt, model_config.model_id)
            
            # Get optimized parameters
            model_params = ai_config.get_optimized_parameters(model_config, request_type)
            
            # Execute with fallback chain
            response = await self._execute_with_fallbacks(
                optimized_prompt, model_config, model_params, priority
            )
            
            if response:
                # Cache successful response
                await self._cache_response(cache_key, response, template.cache_ttl_hours)
                
                # Track performance
                response_time = time.time() - start_time
                self._update_performance_metrics(model_config, response_time, len(optimized_prompt))
                
                return self._format_response(response, cached=False, response_time=response_time)
            else:
                self.performance_metrics['requests_failed'] += 1
                return self._get_fallback_response(request_type)
        
        except Exception as e:
            logger.error(f"Error in AI service: {e}")
            self.performance_metrics['requests_failed'] += 1
            return self._get_fallback_response(request_type, error=str(e))
    
    async def _execute_with_fallbacks(self, prompt: str, primary_model: Any, 
                                    params: Dict[str, Any], priority: str) -> Optional[str]:
        """
        Execute AI request with intelligent fallback chain
        """
        # Try primary model
        response = await self._invoke_model(prompt, primary_model, params)
        if response:
            return response
        
        # Circuit breaker check
        if self._is_circuit_breaker_open(primary_model.model_id):
            logger.warning(f"Circuit breaker open for {primary_model.model_id}, using fallback")
        
        # Try fallback models
        fallback_models = ai_config.get_fallback_chain(AIModel(primary_model.model_id))
        
        for fallback_model_enum in fallback_models:
            fallback_config = ai_config.model_configs[fallback_model_enum]
            
            if self._is_circuit_breaker_open(fallback_config.model_id):
                continue
            
            logger.info(f"Trying fallback model: {fallback_config.model_id}")
            response = await self._invoke_model(prompt, fallback_config, params)
            if response:
                return response
        
        return None
    
    async def _invoke_model(self, prompt: str, model_config: Any, 
                          params: Dict[str, Any]) -> Optional[str]:
        """
        Invoke specific AI model with error handling and circuit breaker
        """
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open(model_config.model_id):
                return None
            
            # Prepare request based on model type
            if 'claude' in model_config.model_id:
                body = self._prepare_claude_request(prompt, params)
            elif 'titan' in model_config.model_id:
                body = self._prepare_titan_request(prompt, params)
            elif 'llama' in model_config.model_id:
                body = self._prepare_llama_request(prompt, params)
            else:
                # Generic request format
                body = self._prepare_generic_request(prompt, params)
            
            # Invoke model
            response = self.bedrock_runtime.invoke_model(
                modelId=model_config.model_id,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            generated_text = self._extract_text_from_response(response_body, model_config.model_id)
            
            # Reset circuit breaker on success
            self._reset_circuit_breaker(model_config.model_id)
            
            return generated_text
        
        except ClientError as e:
            logger.error(f"Bedrock error for {model_config.model_id}: {e}")
            self._record_model_failure(model_config.model_id)
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {model_config.model_id}: {e}")
            self._record_model_failure(model_config.model_id)
            return None
    
    def _prepare_claude_request(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request for Claude models"""
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": params.get('max_tokens', 1000),
            "temperature": params.get('temperature', 0.3),
            "top_p": params.get('top_p', 0.9),
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
    
    def _prepare_titan_request(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request for Titan models"""
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": params.get('max_tokens', 1000),
                "temperature": params.get('temperature', 0.3),
                "topP": params.get('top_p', 0.9),
                "stopSequences": ["Human:", "Assistant:"]
            }
        }
    
    def _prepare_llama_request(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request for Llama models"""
        return {
            "prompt": prompt,
            "max_gen_len": params.get('max_tokens', 1000),
            "temperature": params.get('temperature', 0.3),
            "top_p": params.get('top_p', 0.9)
        }
    
    def _prepare_generic_request(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare generic request format"""
        return {
            "prompt": prompt,
            "max_tokens": params.get('max_tokens', 1000),
            "temperature": params.get('temperature', 0.3),
            "top_p": params.get('top_p', 0.9)
        }
    
    def _extract_text_from_response(self, response_body: Dict[str, Any], model_id: str) -> Optional[str]:
        """Extract text from model response based on model type"""
        try:
            if 'claude' in model_id:
                return response_body.get('content', [{}])[0].get('text', '')
            elif 'titan' in model_id:
                return response_body.get('results', [{}])[0].get('outputText', '')
            elif 'llama' in model_id:
                return response_body.get('generation', '')
            else:
                # Try common response formats
                return (response_body.get('text') or 
                       response_body.get('generated_text') or
                       response_body.get('output') or '')
        except (KeyError, IndexError, TypeError):
            logger.error(f"Failed to extract text from response: {response_body}")
            return None
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available"""
        try:
            cached_data = self.caching_service.get_cached_data(cache_key, 'ai_response')
            return cached_data
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    async def _cache_response(self, cache_key: str, response: str, ttl_hours: int) -> None:
        """Cache AI response for future use"""
        try:
            cache_data = {
                'response': response,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0'
            }
            self.caching_service.set_cached_data(
                cache_key, cache_data, 'ai_response', ttl_hours
            )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _map_request_to_template(self, request_type: str) -> str:
        """Map request type to appropriate prompt template"""
        mapping = {
            'meal_planning': 'meal_planning_optimized',
            'nutrition_analysis': 'nutrition_analysis_fast',
            'recipe_suggestion': 'recipe_suggestion_creative',
            'nutrition_question': 'quick_nutrition_qa',
            'ingredient_substitute': 'ingredient_substitution',
            'general_question': 'quick_nutrition_qa'
        }
        return mapping.get(request_type, 'quick_nutrition_qa')
    
    def _assess_complexity(self, user_input: Dict[str, Any]) -> float:
        """Assess the complexity of the request (1-10 scale)"""
        complexity = 5.0  # Base complexity
        
        # Increase complexity based on input characteristics
        if len(str(user_input)) > 500:
            complexity += 1.0
        
        if any(word in str(user_input).lower() for word in 
               ['analyze', 'compare', 'detailed', 'complex', 'multiple']):
            complexity += 1.5
        
        if 'dietary_restrictions' in user_input and user_input['dietary_restrictions']:
            complexity += 0.5
        
        if 'household_size' in user_input and int(user_input.get('household_size', 1)) > 4:
            complexity += 0.5
        
        return min(complexity, 10.0)
    
    def _is_circuit_breaker_open(self, model_id: str) -> bool:
        """Check if circuit breaker is open for a model"""
        if model_id not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[model_id]
        if breaker['failures'] >= 3:
            # Check if cool-down period has passed
            if datetime.utcnow() - breaker['last_failure'] > timedelta(minutes=5):
                # Reset circuit breaker
                self.circuit_breakers[model_id] = {'failures': 0, 'last_failure': None}
                return False
            return True
        return False
    
    def _record_model_failure(self, model_id: str) -> None:
        """Record model failure for circuit breaker"""
        if model_id not in self.circuit_breakers:
            self.circuit_breakers[model_id] = {'failures': 0, 'last_failure': None}
        
        self.circuit_breakers[model_id]['failures'] += 1
        self.circuit_breakers[model_id]['last_failure'] = datetime.utcnow()
    
    def _reset_circuit_breaker(self, model_id: str) -> None:
        """Reset circuit breaker on successful request"""
        if model_id in self.circuit_breakers:
            self.circuit_breakers[model_id] = {'failures': 0, 'last_failure': None}
    
    def _update_performance_metrics(self, model_config: Any, response_time: float, 
                                  prompt_length: int) -> None:
        """Update performance metrics"""
        self.performance_metrics['requests_total'] += 1
        self.performance_metrics['total_tokens_used'] += prompt_length
        
        # Estimate cost
        estimated_cost = ai_config.estimate_cost(model_config, prompt_length)
        self.performance_metrics['total_cost'] += estimated_cost
        
        # Update average response time
        total_requests = self.performance_metrics['requests_total']
        current_avg = self.performance_metrics['avg_response_time']
        self.performance_metrics['avg_response_time'] = (
            (current_avg * (total_requests - 1) + response_time) / total_requests
        )
        
        # Track model usage
        model_id = model_config.model_id
        if model_id not in self.performance_metrics['model_usage']:
            self.performance_metrics['model_usage'][model_id] = 0
        self.performance_metrics['model_usage'][model_id] += 1
    
    def _format_response(self, response: str, cached: bool = False, 
                        response_time: float = 0.0) -> Dict[str, Any]:
        """Format AI response with metadata"""
        return {
            'success': True,
            'response': response,
            'cached': cached,
            'response_time': response_time,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_fallback_response(self, request_type: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Generate fallback response when AI fails"""
        fallback_responses = {
            'meal_planning': "I'm temporarily unable to generate a detailed meal plan. Here's a quick suggestion: Try a balanced meal with lean protein, vegetables, and whole grains.",
            'nutrition_analysis': "I'm having trouble analyzing that food item right now. Please try again later or consult a nutrition database.",
            'recipe_suggestion': "I can't generate a recipe at the moment. Try searching for recipes online or check your favorite cookbook.",
            'nutrition_question': "I'm experiencing technical difficulties. For immediate nutrition advice, please consult a healthcare professional.",
            'ingredient_substitute': "I can't suggest substitutions right now. Try using common substitutes like Greek yogurt for sour cream, or applesauce for oil in baking."
        }
        
        return {
            'success': False,
            'response': fallback_responses.get(request_type, "I'm temporarily unavailable. Please try again later."),
            'error': error,
            'fallback': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        total_requests = self.performance_metrics['requests_total']
        if total_requests == 0:
            return {'message': 'No requests processed yet'}
        
        cache_hit_rate = self.performance_metrics['requests_cached'] / total_requests
        error_rate = self.performance_metrics['requests_failed'] / total_requests
        
        return {
            'total_requests': total_requests,
            'cache_hit_rate': cache_hit_rate,
            'error_rate': error_rate,
            'avg_response_time': self.performance_metrics['avg_response_time'],
            'total_cost': self.performance_metrics['total_cost'],
            'cost_per_request': self.performance_metrics['total_cost'] / total_requests,
            'model_usage_distribution': self.performance_metrics['model_usage'],
            'circuit_breaker_status': self.circuit_breakers,
            'optimization_suggestions': self._get_optimization_suggestions()
        }
    
    def _get_optimization_suggestions(self) -> List[str]:
        """Get AI service optimization suggestions"""
        suggestions = []
        metrics = self.performance_metrics
        
        cache_hit_rate = metrics['requests_cached'] / max(metrics['requests_total'], 1)
        if cache_hit_rate < 0.6:
            suggestions.append("Consider extending cache TTL or improving cache key strategy")
        
        if metrics['avg_response_time'] > 2.0:
            suggestions.append("Response times are high - consider using faster models for simple queries")
        
        if metrics['total_cost'] / max(metrics['requests_total'], 1) > 0.02:
            suggestions.append("Cost per request is high - consider optimizing prompts or using cheaper models")
        
        return suggestions


# Global instance
enhanced_ai_service = EnhancedAIService()
