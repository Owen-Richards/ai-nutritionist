"""
AI Nutritionist Cost Optimizer
Advanced cost optimization to prevent wasteful spending on invalid requests
"""

import boto3
import os
import json
import time
import re
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CostOptimizationAction(Enum):
    ALLOW = "allow"
    WARN = "warn"
    THROTTLE = "throttle"
    REJECT = "reject"
    PREMIUM_ONLY = "premium_only"

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    reason: str
    estimated_cost: float
    optimization_action: CostOptimizationAction
    metadata: Dict[str, Any]

class IntelligentCostOptimizer:
    """Smart cost optimization to prevent wasteful API usage"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.cloudwatch = boto3.client('cloudwatch')
        
        # Cost optimization tables
        self.cost_cache_table = self.dynamodb.Table('ai-nutritionist-cost-cache')
        self.user_patterns_table = self.dynamodb.Table('ai-nutritionist-user-patterns')
        self.optimization_metrics_table = self.dynamodb.Table('ai-nutritionist-optimization-metrics')
        
        # Cost rates and thresholds
        self.COST_RATES = {
            'bedrock_claude_input': 0.00025,   # per 1K tokens
            'bedrock_claude_output': 0.00125,  # per 1K tokens
            'edamam_recipe_api': 0.001,        # per API call
            'dynamodb_read': 0.0000125,        # per read unit
            'dynamodb_write': 0.0000125,       # per write unit
            'aws_sms': 0.00645,                # per SMS
            'whatsapp_message': 0.005,         # per WhatsApp message
        }
        
        # Smart validation thresholds
        self.OPTIMIZATION_THRESHOLDS = {
            'daily_cost_limit': Decimal('2.00'),
            'suspicious_request_threshold': 0.7,  # Confidence score
            'repetitive_request_window': 300,     # 5 minutes
            'max_similar_requests': 3,
            'low_value_request_cost_limit': 0.01,
            'premium_user_multiplier': 5.0,
        }

    def validate_request_cost_efficiency(self, 
                                       user_phone: str, 
                                       request_type: str, 
                                       message_content: str,
                                       user_tier: str = 'free') -> ValidationResult:
        """
        Intelligent validation to prevent wasteful costs
        Returns validation result with cost optimization recommendations
        """
        try:
            # 1. Quick validation checks (no cost)
            basic_validation = self._basic_request_validation(message_content, request_type)
            if not basic_validation.is_valid:
                return basic_validation
            
            # 2. Check user's cost patterns and limits
            cost_check = self._check_user_cost_limits(user_phone, request_type, user_tier)
            if cost_check.optimization_action in [CostOptimizationAction.REJECT, CostOptimizationAction.THROTTLE]:
                return cost_check
            
            # 3. Detect duplicate/similar requests (prevent waste)
            duplicate_check = self._detect_duplicate_requests(user_phone, message_content, request_type)
            if duplicate_check.optimization_action != CostOptimizationAction.ALLOW:
                return duplicate_check
            
            # 4. Estimate request value vs cost
            value_analysis = self._analyze_request_value(message_content, request_type, user_tier)
            if value_analysis.optimization_action != CostOptimizationAction.ALLOW:
                return value_analysis
            
            # 5. Check for suspicious patterns
            suspicion_check = self._detect_suspicious_patterns(user_phone, message_content, request_type)
            if suspicion_check.optimization_action != CostOptimizationAction.ALLOW:
                return suspicion_check
            
            # Request is valid and cost-efficient
            estimated_cost = self._estimate_request_cost(request_type, message_content)
            
            return ValidationResult(
                is_valid=True,
                confidence=0.95,
                reason="request_approved_cost_efficient",
                estimated_cost=estimated_cost,
                optimization_action=CostOptimizationAction.ALLOW,
                metadata={
                    'user_tier': user_tier,
                    'estimated_tokens': self._estimate_token_usage(message_content, request_type),
                    'cost_category': 'efficient'
                }
            )
            
        except Exception as e:
            logger.error(f"Error in cost optimization validation: {str(e)}")
            # Fail safe - allow but track error
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                reason="validation_error_fail_safe",
                estimated_cost=0.01,
                optimization_action=CostOptimizationAction.WARN,
                metadata={'error': str(e)}
            )

    def _basic_request_validation(self, message_content: str, request_type: str) -> ValidationResult:
        """Basic validation that requires no API costs"""
        
        # Empty or too short messages
        if not message_content or len(message_content.strip()) < 3:
            return ValidationResult(
                is_valid=False,
                confidence=1.0,
                reason="message_too_short",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.REJECT,
                metadata={'content_length': len(message_content)}
            )
        
        # Extremely long messages (likely spam)
        if len(message_content) > 2000:
            return ValidationResult(
                is_valid=False,
                confidence=0.95,
                reason="message_too_long_likely_spam",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.REJECT,
                metadata={'content_length': len(message_content)}
            )
        
        # Check for obvious spam patterns
        spam_indicators = ['click here', 'free money', 'congratulations', 'you won', 'urgent action required']
        spam_score = sum(1 for indicator in spam_indicators if indicator.lower() in message_content.lower())
        
        if spam_score >= 2:
            return ValidationResult(
                is_valid=False,
                confidence=0.9,
                reason="spam_patterns_detected",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.REJECT,
                metadata={'spam_indicators': spam_score}
            )
        
        # Valid basic checks
        return ValidationResult(
            is_valid=True,
            confidence=0.8,
            reason="basic_validation_passed",
            estimated_cost=0.0,
            optimization_action=CostOptimizationAction.ALLOW,
            metadata={}
        )

    def _check_user_cost_limits(self, user_phone: str, request_type: str, user_tier: str) -> ValidationResult:
        """Check if user is within cost limits"""
        try:
            # Get today's costs for user
            today = datetime.utcnow().strftime('%Y-%m-%d')
            daily_cost = self._get_user_daily_cost(user_phone, today)
            
            # Adjust limits based on user tier
            if user_tier == 'premium':
                daily_limit = self.OPTIMIZATION_THRESHOLDS['daily_cost_limit'] * self.OPTIMIZATION_THRESHOLDS['premium_user_multiplier']
            else:
                daily_limit = self.OPTIMIZATION_THRESHOLDS['daily_cost_limit']
            
            # Check if approaching limit
            if daily_cost >= daily_limit:
                return ValidationResult(
                    is_valid=False,
                    confidence=1.0,
                    reason="daily_cost_limit_exceeded",
                    estimated_cost=0.0,
                    optimization_action=CostOptimizationAction.REJECT if user_tier == 'free' else CostOptimizationAction.PREMIUM_ONLY,
                    metadata={
                        'daily_cost': float(daily_cost),
                        'daily_limit': float(daily_limit),
                        'user_tier': user_tier
                    }
                )
            
            # Warning threshold (80% of limit)
            if daily_cost >= daily_limit * 0.8:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.7,
                    reason="approaching_cost_limit",
                    estimated_cost=self._estimate_request_cost(request_type, ''),
                    optimization_action=CostOptimizationAction.WARN,
                    metadata={
                        'daily_cost': float(daily_cost),
                        'daily_limit': float(daily_limit),
                        'percentage_used': float((daily_cost / daily_limit) * 100)
                    }
                )
            
            # Within limits
            return ValidationResult(
                is_valid=True,
                confidence=0.9,
                reason="within_cost_limits",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.ALLOW,
                metadata={'daily_cost': float(daily_cost)}
            )
            
        except Exception as e:
            logger.error(f"Error checking user cost limits: {str(e)}")
            return ValidationResult(
                is_valid=True,
                confidence=0.5,
                reason="cost_check_error",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.WARN,
                metadata={'error': str(e)}
            )

    def _detect_duplicate_requests(self, user_phone: str, message_content: str, request_type: str) -> ValidationResult:
        """Detect duplicate or very similar requests to prevent waste"""
        try:
            # Check recent requests from this user
            cutoff_time = int(time.time()) - self.OPTIMIZATION_THRESHOLDS['repetitive_request_window']
            
            response = self.user_patterns_table.query(
                KeyConditionExpression='user_phone = :phone',
                FilterExpression='request_timestamp > :cutoff',
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':cutoff': cutoff_time
                },
                ScanIndexForward=False,  # Latest first
                Limit=10
            )
            
            recent_requests = response.get('Items', [])
            
            # Check for exact duplicates
            exact_matches = 0
            similar_matches = 0
            
            for request in recent_requests:
                stored_content = request.get('message_content', '')
                stored_type = request.get('request_type', '')
                
                # Exact match
                if stored_content.lower().strip() == message_content.lower().strip() and stored_type == request_type:
                    exact_matches += 1
                
                # Similar match (80% similarity)
                elif self._calculate_similarity(stored_content, message_content) > 0.8 and stored_type == request_type:
                    similar_matches += 1
            
            # Too many exact duplicates
            if exact_matches >= 2:
                return ValidationResult(
                    is_valid=False,
                    confidence=0.95,
                    reason="duplicate_request_detected",
                    estimated_cost=0.0,
                    optimization_action=CostOptimizationAction.REJECT,
                    metadata={
                        'exact_matches': exact_matches,
                        'time_window': self.OPTIMIZATION_THRESHOLDS['repetitive_request_window']
                    }
                )
            
            # Too many similar requests
            if similar_matches >= self.OPTIMIZATION_THRESHOLDS['max_similar_requests']:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.8,
                    reason="similar_requests_detected",
                    estimated_cost=self._estimate_request_cost(request_type, message_content),
                    optimization_action=CostOptimizationAction.THROTTLE,
                    metadata={
                        'similar_matches': similar_matches,
                        'throttle_reason': 'potential_duplicate_pattern'
                    }
                )
            
            # Store this request for future duplicate detection
            self._store_request_pattern(user_phone, message_content, request_type)
            
            return ValidationResult(
                is_valid=True,
                confidence=0.9,
                reason="no_duplicates_detected",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.ALLOW,
                metadata={'recent_requests_count': len(recent_requests)}
            )
            
        except Exception as e:
            logger.error(f"Error detecting duplicate requests: {str(e)}")
            return ValidationResult(
                is_valid=True,
                confidence=0.7,
                reason="duplicate_check_error",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.ALLOW,
                metadata={'error': str(e)}
            )

    def _analyze_request_value(self, message_content: str, request_type: str, user_tier: str) -> ValidationResult:
        """Analyze if request provides good value for cost"""
        
        # Categorize request types by value
        high_value_types = ['meal_plan', 'nutrition_analysis', 'dietary_advice']
        medium_value_types = ['recipe_search', 'grocery_list']
        low_value_types = ['simple_message', 'general_question']
        
        # Calculate value score based on content quality
        value_score = self._calculate_content_value_score(message_content, request_type)
        estimated_cost = self._estimate_request_cost(request_type, message_content)
        
        # Low value, high cost requests
        if (request_type in low_value_types and 
            estimated_cost > self.OPTIMIZATION_THRESHOLDS['low_value_request_cost_limit'] and
            value_score < 0.5):
            
            return ValidationResult(
                is_valid=True,
                confidence=0.8,
                reason="low_value_high_cost_request",
                estimated_cost=estimated_cost,
                optimization_action=CostOptimizationAction.WARN,
                metadata={
                    'value_score': value_score,
                    'cost_category': 'low_value_high_cost',
                    'suggestion': 'Consider rephrasing for better assistance'
                }
            )
        
        # High value requests - proceed normally
        if request_type in high_value_types or value_score > 0.8:
            return ValidationResult(
                is_valid=True,
                confidence=0.95,
                reason="high_value_request",
                estimated_cost=estimated_cost,
                optimization_action=CostOptimizationAction.ALLOW,
                metadata={
                    'value_score': value_score,
                    'cost_category': 'high_value'
                }
            )
        
        # Medium value - normal processing
        return ValidationResult(
            is_valid=True,
            confidence=0.85,
            reason="medium_value_request",
            estimated_cost=estimated_cost,
            optimization_action=CostOptimizationAction.ALLOW,
            metadata={
                'value_score': value_score,
                'cost_category': 'medium_value'
            }
        )

    def _detect_suspicious_patterns(self, user_phone: str, message_content: str, request_type: str) -> ValidationResult:
        """Detect suspicious usage patterns that might indicate abuse"""
        
        # Check for bot-like behavior
        bot_indicators = [
            len(message_content.split()) < 3,  # Very short messages
            message_content.count('?') > 5,    # Excessive questions
            request_type == 'simple_message' and len(message_content) > 500,  # Long simple messages
            bool(re.search(r'http[s]?://', message_content)),  # Contains URLs
            bool(re.search(r'\b\d{10,}\b', message_content)),  # Contains long numbers (phone/account)
        ]
        
        suspicion_score = sum(bot_indicators) / len(bot_indicators)
        
        if suspicion_score > self.OPTIMIZATION_THRESHOLDS['suspicious_request_threshold']:
            return ValidationResult(
                is_valid=False,
                confidence=0.85,
                reason="suspicious_usage_pattern",
                estimated_cost=0.0,
                optimization_action=CostOptimizationAction.REJECT,
                metadata={
                    'suspicion_score': suspicion_score,
                    'indicators': bot_indicators
                }
            )
        
        return ValidationResult(
            is_valid=True,
            confidence=0.9,
            reason="no_suspicious_patterns",
            estimated_cost=0.0,
            optimization_action=CostOptimizationAction.ALLOW,
            metadata={'suspicion_score': suspicion_score}
        )

    def _estimate_request_cost(self, request_type: str, message_content: str) -> float:
        """Estimate the cost of processing this request"""
        
        base_costs = {
            'meal_plan': 0.05,      # Complex AI processing
            'nutrition_analysis': 0.03,
            'recipe_search': 0.02,
            'grocery_list': 0.02,
            'dietary_advice': 0.04,
            'simple_message': 0.01
        }
        
        base_cost = base_costs.get(request_type, 0.02)
        
        # Adjust based on message complexity
        word_count = len(message_content.split())
        if word_count > 50:
            base_cost *= 1.5  # Complex requests cost more
        elif word_count < 5:
            base_cost *= 0.5  # Simple requests cost less
            
        return base_cost

    def _estimate_token_usage(self, message_content: str, request_type: str) -> int:
        """Estimate token usage for AI processing"""
        
        # Rough token estimation (4 chars = 1 token)
        input_tokens = len(message_content) // 4
        
        # Output tokens based on request type
        output_tokens_map = {
            'meal_plan': 500,
            'nutrition_analysis': 300,
            'recipe_search': 200,
            'grocery_list': 150,
            'dietary_advice': 400,
            'simple_message': 50
        }
        
        output_tokens = output_tokens_map.get(request_type, 100)
        
        return input_tokens + output_tokens

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simple implementation)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

    def _calculate_content_value_score(self, message_content: str, request_type: str) -> float:
        """Calculate the value score of request content"""
        
        # Keywords that indicate high-value nutrition requests
        high_value_keywords = [
            'diabetes', 'allergies', 'weight loss', 'muscle gain', 'meal plan',
            'nutrition', 'calories', 'protein', 'diet', 'healthy', 'recipe',
            'ingredients', 'grocery', 'budget', 'family', 'vegetarian', 'vegan'
        ]
        
        message_lower = message_content.lower()
        keyword_matches = sum(1 for keyword in high_value_keywords if keyword in message_lower)
        
        # Base score from keyword matches
        keyword_score = min(keyword_matches / 3, 1.0)  # Cap at 1.0
        
        # Bonus for specific details
        detail_score = 0.0
        if any(char.isdigit() for char in message_content):  # Contains numbers (portions, budget, etc.)
            detail_score += 0.2
        if len(message_content.split()) > 10:  # Detailed description
            detail_score += 0.2
        if '?' in message_content:  # Asking specific questions
            detail_score += 0.1
            
        return min(keyword_score + detail_score, 1.0)

    def _get_user_daily_cost(self, user_phone: str, date: str) -> Decimal:
        """Get user's total costs for a specific date"""
        try:
            # This would integrate with your existing cost tracking
            from .cost_tracking import UserCostTracker
            cost_tracker = UserCostTracker()
            return cost_tracker.get_monthly_cost(user_phone)  # Adapt for daily
        except Exception:
            return Decimal('0')

    def _store_request_pattern(self, user_phone: str, message_content: str, request_type: str):
        """Store request pattern for duplicate detection"""
        try:
            self.user_patterns_table.put_item(
                Item={
                    'user_phone': user_phone,
                    'request_timestamp': int(time.time()),
                    'message_content': message_content[:500],  # Truncate for storage
                    'request_type': request_type,
                    'ttl': int(time.time()) + 86400  # 24 hour TTL
                }
            )
        except Exception as e:
            logger.error(f"Error storing request pattern: {str(e)}")

    def track_optimization_metrics(self, validation_result: ValidationResult, user_phone: str):
        """Track cost optimization metrics for monitoring"""
        try:
            self.optimization_metrics_table.put_item(
                Item={
                    'timestamp': int(time.time()),
                    'user_phone': user_phone,
                    'optimization_action': validation_result.optimization_action.value,
                    'estimated_cost_saved': validation_result.estimated_cost if validation_result.optimization_action != CostOptimizationAction.ALLOW else 0.0,
                    'confidence': validation_result.confidence,
                    'reason': validation_result.reason,
                    'date': datetime.utcnow().strftime('%Y-%m-%d'),
                    'ttl': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days TTL
                }
            )
            
            # Send CloudWatch metrics
            self.cloudwatch.put_metric_data(
                Namespace='AI-Nutritionist/CostOptimization',
                MetricData=[
                    {
                        'MetricName': 'RequestsOptimized',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Action', 'Value': validation_result.optimization_action.value}
                        ]
                    },
                    {
                        'MetricName': 'EstimatedCostSaved',
                        'Value': validation_result.estimated_cost if validation_result.optimization_action != CostOptimizationAction.ALLOW else 0.0,
                        'Unit': 'None'
                    }
                ]
            )
            
        except Exception as e:
            logger.error(f"Error tracking optimization metrics: {str(e)}")

# Usage example function
def optimize_request_cost(user_phone: str, message: str, request_type: str, user_tier: str = 'free') -> Dict[str, Any]:
    """Main function to optimize request costs"""
    
    optimizer = IntelligentCostOptimizer()
    validation_result = optimizer.validate_request_cost_efficiency(
        user_phone=user_phone,
        request_type=request_type,
        message_content=message,
        user_tier=user_tier
    )
    
    # Track metrics
    optimizer.track_optimization_metrics(validation_result, user_phone)
    
    return {
        'should_process': validation_result.is_valid and validation_result.optimization_action == CostOptimizationAction.ALLOW,
        'action': validation_result.optimization_action.value,
        'reason': validation_result.reason,
        'estimated_cost': validation_result.estimated_cost,
        'confidence': validation_result.confidence,
        'metadata': validation_result.metadata,
        'user_message': _get_user_message(validation_result)
    }

def _get_user_message(validation_result: ValidationResult) -> Optional[str]:
    """Get user-friendly message based on optimization action"""
    
    messages = {
        CostOptimizationAction.REJECT: "Sorry, I can't process this request. Please try rephrasing your question about nutrition or meal planning.",
        CostOptimizationAction.THROTTLE: "I notice you've sent similar requests recently. Let me help you with something new!",
        CostOptimizationAction.WARN: "You're approaching your daily usage limit. Consider upgrading to premium for unlimited access.",
        CostOptimizationAction.PREMIUM_ONLY: "You've reached your daily limit. Upgrade to premium to continue using the service.",
        CostOptimizationAction.ALLOW: None
    }
    
    return messages.get(validation_result.optimization_action)
