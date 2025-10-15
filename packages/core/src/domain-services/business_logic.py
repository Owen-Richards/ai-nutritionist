"""
Pure domain service for business logic and cost optimization
Separated from infrastructure concerns following hexagonal architecture
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from packages.core.src.interfaces.repositories import BusinessRepository, UserRepository
from packages.core.src.interfaces.services import AnalyticsService, MonitoringService
from packages.core.src.interfaces.domain import (
    CostOptimizationResult,
    BusinessDomainService,
    UserTier
)

logger = logging.getLogger(__name__)


class CostOptimizationAction(Enum):
    ALLOW = "allow"
    WARN = "warn"
    THROTTLE = "throttle"
    REJECT = "reject"
    PREMIUM_ONLY = "premium_only"


class BusinessLogicService(BusinessDomainService):
    """Pure domain service for business logic - no infrastructure dependencies"""
    
    def __init__(
        self,
        business_repo: BusinessRepository,
        user_repo: UserRepository,
        analytics_service: AnalyticsService,
        monitoring_service: MonitoringService
    ):
        self.business_repo = business_repo
        self.user_repo = user_repo
        self.analytics = analytics_service
        self.monitoring = monitoring_service
        
        # Business rules and thresholds
        self.COST_RATES = {
            'bedrock_claude_input': 0.00025,   # per 1K tokens
            'bedrock_claude_output': 0.00125,  # per 1K tokens
            'edamam_recipe_search': 0.002,     # per request
            'edamam_nutrition_analysis': 0.003, # per request
            'sms_message': 0.0075,             # per message
            'whatsapp_message': 0.005,         # per message
        }
        
        self.OPTIMIZATION_THRESHOLDS = {
            'daily_cost_limit_free': 0.50,
            'daily_cost_limit_premium': 5.00,
            'daily_cost_limit_family': 10.00,
            'daily_cost_limit_enterprise': -1,  # unlimited
            'repetitive_request_window': 3600,  # 1 hour
            'max_similar_requests': 3,
            'low_quality_request_threshold': 0.3,
            'spam_detection_threshold': 0.8
        }
    
    def validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Validate business-specific rules"""
        # Validate cost optimization data
        if 'estimated_cost' in data:
            cost = data['estimated_cost']
            if not isinstance(cost, (int, float)) or cost < 0:
                return False
        
        # Validate user tier
        if 'user_tier' in data:
            valid_tiers = [tier.value for tier in UserTier]
            if data['user_tier'] not in valid_tiers:
                return False
        
        return True
    
    def calculate_user_value(self, user_profile: Dict[str, Any], usage_data: Dict[str, Any]) -> float:
        """Calculate user lifetime value using domain logic"""
        ltv = 0.0
        
        # Base value from tier
        tier_values = {
            'free': 0.0,
            'premium': 120.0,    # $10/month * 12 months
            'family': 240.0,     # $20/month * 12 months
            'enterprise': 1200.0  # $100/month * 12 months
        }
        
        user_tier = user_profile.get('premium_tier', 'free')
        ltv += tier_values.get(user_tier, 0.0)
        
        # Usage-based value
        api_usage = usage_data.get('total_requests', 0)
        if api_usage > 1000:
            ltv += 50.0  # High-usage user
        elif api_usage > 100:
            ltv += 20.0  # Moderate-usage user
        
        # Engagement multiplier
        days_active = usage_data.get('days_active', 0)
        if days_active > 365:
            ltv *= 1.5  # Loyal user multiplier
        elif days_active > 90:
            ltv *= 1.2  # Regular user multiplier
        
        return ltv
    
    def determine_optimal_pricing(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal pricing strategy for user using domain logic"""
        current_tier = user_profile.get('premium_tier', 'free')
        usage_patterns = user_profile.get('usage_patterns', {})
        
        # Analyze usage patterns
        daily_requests = usage_patterns.get('avg_daily_requests', 0)
        cost_per_request = usage_patterns.get('avg_cost_per_request', 0.01)
        
        # Calculate break-even points
        monthly_cost = daily_requests * cost_per_request * 30
        
        recommendations = {
            'current_tier': current_tier,
            'recommended_tier': current_tier,
            'monthly_value': monthly_cost,
            'savings_potential': 0.0,
            'upgrade_reason': None
        }
        
        # Upgrade recommendations based on domain rules
        if current_tier == 'free' and monthly_cost > 5.0:
            recommendations.update({
                'recommended_tier': 'premium',
                'savings_potential': max(0, monthly_cost - 10.0),
                'upgrade_reason': 'cost_optimization'
            })
        elif current_tier == 'premium' and daily_requests > 100:
            recommendations.update({
                'recommended_tier': 'family',
                'savings_potential': max(0, monthly_cost - 20.0),
                'upgrade_reason': 'high_usage'
            })
        
        return recommendations
    
    async def validate_request_cost_optimization(
        self, 
        user_phone: str, 
        request_type: str, 
        message_content: str
    ) -> CostOptimizationResult:
        """Validate request for cost optimization using domain rules"""
        try:
            # Get user information
            user = await self.user_repo.get_user_by_phone(user_phone)
            if not user:
                return self._create_rejection_result("User not found")
            
            user_tier = user.get('premium_tier', 'free')
            
            # Step 1: Basic request validation
            basic_validation = self._validate_request_quality(message_content, request_type)
            if not basic_validation.is_valid:
                return basic_validation
            
            # Step 2: Check user cost limits
            cost_limit_check = await self._check_user_cost_limits(user_phone, request_type, user_tier)
            if not cost_limit_check.is_valid:
                return cost_limit_check
            
            # Step 3: Detect duplicate requests
            duplicate_check = await self._detect_duplicate_requests(user_phone, message_content, request_type)
            if not duplicate_check.is_valid:
                return duplicate_check
            
            # Step 4: Calculate estimated cost
            estimated_cost = self._estimate_request_cost(request_type, message_content)
            
            # Track metrics
            await self.monitoring.track_metric(
                'cost_optimization.request_validated',
                1.0,
                {'user_tier': user_tier, 'request_type': request_type}
            )
            
            return CostOptimizationResult(
                is_valid=True,
                confidence=0.9,
                reason="request_approved",
                estimated_cost=estimated_cost,
                recommended_action=CostOptimizationAction.ALLOW.value,
                user_message=None,
                metadata={
                    'user_tier': user_tier,
                    'estimated_cost': estimated_cost
                }
            )
        
        except Exception as e:
            logger.error(f"Error in cost optimization validation: {e}")
            return self._create_error_result("Validation error occurred")
    
    async def track_revenue_event(
        self, 
        user_phone: str, 
        event_type: str, 
        amount: float, 
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Track revenue event using domain logic"""
        try:
            event_data = {
                'user_phone': user_phone,
                'event_type': event_type,
                'revenue_amount': amount,
                'currency': 'USD',
                'metadata': metadata or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Validate revenue event using domain rules
            if not self._validate_revenue_event(event_data):
                logger.warning(f"Invalid revenue event: {event_data}")
                return False
            
            # Save to repository
            success = await self.business_repo.track_revenue_event(event_data)
            
            if success:
                # Track analytics
                await self.analytics.track_user_event(
                    user_id=user_phone,
                    event=f'revenue.{event_type}',
                    properties={
                        'amount': amount,
                        'currency': 'USD',
                        'metadata': metadata
                    }
                )
                
                # Track monitoring metrics
                await self.monitoring.track_metric(
                    f'revenue.{event_type}',
                    amount,
                    {'user_tier': metadata.get('user_tier', 'unknown') if metadata else 'unknown'}
                )
            
            return success
        
        except Exception as e:
            logger.error(f"Error tracking revenue event: {e}")
            return False
    
    def _validate_request_quality(self, message_content: str, request_type: str) -> CostOptimizationResult:
        """Validate request quality using domain rules"""
        if not message_content or len(message_content.strip()) < 3:
            return self._create_rejection_result("Message too short")
        
        # Check for spam patterns
        spam_indicators = ['buy now', 'click here', 'free money', 'urgent', '!!!']
        spam_score = sum(1 for indicator in spam_indicators if indicator.lower() in message_content.lower())
        
        if spam_score >= 2:
            return self._create_rejection_result("Potential spam detected")
        
        # Check for nutrition-related content
        nutrition_keywords = ['meal', 'food', 'recipe', 'diet', 'nutrition', 'calorie', 'protein', 'vitamin']
        has_nutrition_content = any(keyword in message_content.lower() for keyword in nutrition_keywords)
        
        if not has_nutrition_content and request_type in ['meal_plan', 'nutrition_advice']:
            return CostOptimizationResult(
                is_valid=False,
                confidence=0.8,
                reason="off_topic_request",
                estimated_cost=0.0,
                recommended_action=CostOptimizationAction.REJECT.value,
                user_message="Please ask nutrition-related questions for personalized meal planning.",
                metadata={'spam_score': spam_score}
            )
        
        return CostOptimizationResult(
            is_valid=True,
            confidence=0.9,
            reason="quality_check_passed",
            estimated_cost=0.0,
            recommended_action=CostOptimizationAction.ALLOW.value,
            user_message=None,
            metadata={'quality_score': 0.9}
        )
    
    async def _check_user_cost_limits(self, user_phone: str, request_type: str, user_tier: str) -> CostOptimizationResult:
        """Check if user is within cost limits using domain rules"""
        try:
            # Get daily cost limit based on tier
            daily_limit = self.OPTIMIZATION_THRESHOLDS.get(f'daily_cost_limit_{user_tier}', 0.50)
            
            if daily_limit == -1:  # Unlimited
                return CostOptimizationResult(
                    is_valid=True,
                    confidence=1.0,
                    reason="unlimited_tier",
                    estimated_cost=0.0,
                    recommended_action=CostOptimizationAction.ALLOW.value,
                    user_message=None,
                    metadata={'tier': user_tier}
                )
            
            # Get user's usage in the last 24 hours
            usage_patterns = await self.business_repo.get_cost_optimization_patterns(user_phone, hours=24)
            
            daily_cost = sum(float(pattern.get('estimated_cost', 0)) for pattern in usage_patterns)
            estimated_request_cost = self._estimate_request_cost(request_type, "")
            
            if daily_cost + estimated_request_cost > daily_limit:
                if user_tier == 'free':
                    return CostOptimizationResult(
                        is_valid=False,
                        confidence=0.95,
                        reason="daily_limit_exceeded",
                        estimated_cost=estimated_request_cost,
                        recommended_action=CostOptimizationAction.PREMIUM_ONLY.value,
                        user_message=f"You've reached your daily limit. Upgrade to premium for unlimited access!",
                        metadata={'daily_cost': daily_cost, 'limit': daily_limit}
                    )
                else:
                    return CostOptimizationResult(
                        is_valid=False,
                        confidence=0.9,
                        reason="tier_limit_exceeded",
                        estimated_cost=estimated_request_cost,
                        recommended_action=CostOptimizationAction.WARN.value,
                        user_message=f"You're approaching your daily usage limit.",
                        metadata={'daily_cost': daily_cost, 'limit': daily_limit}
                    )
            
            return CostOptimizationResult(
                is_valid=True,
                confidence=0.9,
                reason="within_limits",
                estimated_cost=estimated_request_cost,
                recommended_action=CostOptimizationAction.ALLOW.value,
                user_message=None,
                metadata={'daily_cost': daily_cost, 'limit': daily_limit}
            )
        
        except Exception as e:
            logger.error(f"Error checking cost limits: {e}")
            return self._create_error_result("Cost limit check failed")
    
    async def _detect_duplicate_requests(self, user_phone: str, message_content: str, request_type: str) -> CostOptimizationResult:
        """Detect duplicate requests using domain logic"""
        try:
            # Get recent requests
            recent_patterns = await self.business_repo.get_cost_optimization_patterns(user_phone, hours=1)
            
            # Check for exact duplicates
            exact_matches = 0
            similar_matches = 0
            
            for pattern in recent_patterns:
                stored_content = pattern.get('message_content', '')
                stored_type = pattern.get('request_type', '')
                
                # Exact match
                if stored_content.lower().strip() == message_content.lower().strip() and stored_type == request_type:
                    exact_matches += 1
                
                # Similar match (simple similarity check)
                similarity = self._calculate_text_similarity(stored_content, message_content)
                if similarity > 0.8 and stored_type == request_type:
                    similar_matches += 1
            
            # Too many exact duplicates
            if exact_matches >= 2:
                return CostOptimizationResult(
                    is_valid=False,
                    confidence=0.95,
                    reason="duplicate_request_detected",
                    estimated_cost=0.0,
                    recommended_action=CostOptimizationAction.REJECT.value,
                    user_message="I notice you've asked this question recently. Please try asking something different!",
                    metadata={'exact_matches': exact_matches}
                )
            
            # Too many similar requests
            max_similar = self.OPTIMIZATION_THRESHOLDS['max_similar_requests']
            if similar_matches >= max_similar:
                return CostOptimizationResult(
                    is_valid=True,
                    confidence=0.8,
                    reason="similar_requests_detected",
                    estimated_cost=self._estimate_request_cost(request_type, message_content),
                    recommended_action=CostOptimizationAction.THROTTLE.value,
                    user_message="I notice you've sent similar requests recently. Let me help you with something new!",
                    metadata={'similar_matches': similar_matches}
                )
            
            return CostOptimizationResult(
                is_valid=True,
                confidence=0.9,
                reason="no_duplicates_detected",
                estimated_cost=self._estimate_request_cost(request_type, message_content),
                recommended_action=CostOptimizationAction.ALLOW.value,
                user_message=None,
                metadata={'exact_matches': exact_matches, 'similar_matches': similar_matches}
            )
        
        except Exception as e:
            logger.error(f"Error detecting duplicates: {e}")
            return self._create_error_result("Duplicate check failed")
    
    def _estimate_request_cost(self, request_type: str, message_content: str) -> float:
        """Estimate request cost using domain pricing rules"""
        base_costs = {
            'meal_plan': 0.015,      # AI + recipe search
            'nutrition_advice': 0.008, # AI only
            'recipe_search': 0.005,   # Recipe API only
            'general_chat': 0.003     # Basic AI
        }
        
        base_cost = base_costs.get(request_type, 0.005)
        
        # Adjust for message length (longer messages cost more)
        length_multiplier = 1 + (len(message_content) / 1000) * 0.2
        
        return base_cost * length_multiplier
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _validate_revenue_event(self, event_data: Dict[str, Any]) -> bool:
        """Validate revenue event using domain rules"""
        required_fields = ['user_phone', 'event_type', 'revenue_amount', 'currency']
        
        for field in required_fields:
            if field not in event_data:
                return False
        
        # Validate amount
        amount = event_data['revenue_amount']
        if not isinstance(amount, (int, float)) or amount < 0:
            return False
        
        # Validate event type
        valid_event_types = ['subscription', 'affiliate', 'marketplace', 'advertising', 'premium_feature']
        if event_data['event_type'] not in valid_event_types:
            return False
        
        return True
    
    def _create_rejection_result(self, reason: str) -> CostOptimizationResult:
        """Create rejection result"""
        return CostOptimizationResult(
            is_valid=False,
            confidence=0.9,
            reason=reason,
            estimated_cost=0.0,
            recommended_action=CostOptimizationAction.REJECT.value,
            user_message="Sorry, I can't process this request. Please try rephrasing your nutrition question.",
            metadata={'rejection_reason': reason}
        )
    
    def _create_error_result(self, error_message: str) -> CostOptimizationResult:
        """Create error result"""
        return CostOptimizationResult(
            is_valid=True,  # Allow on error to avoid blocking users
            confidence=0.5,
            reason=error_message,
            estimated_cost=0.0,
            recommended_action=CostOptimizationAction.ALLOW.value,
            user_message=None,
            metadata={'error': error_message}
        )
