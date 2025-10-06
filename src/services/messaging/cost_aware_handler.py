"""
Enhanced Cost-Aware Request Handler
Integrates intelligent cost optimization with existing spam protection and rate limiting
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from ..business.cost_optimizer import IntelligentCostOptimizer, CostOptimizationAction, optimize_request_cost
from ..utils.validators import MessageValidator, PhoneValidator
from ...handlers.spam_protection_handler import SpamProtectionService

logger = logging.getLogger(__name__)

class CostAwareRequestHandler:
    """Enhanced request handler that optimizes costs while maintaining functionality"""
    
    def __init__(self):
        self.cost_optimizer = IntelligentCostOptimizer()
        self.spam_protection = SpamProtectionService()
        
        # Cost savings tracking
        self.session_stats = {
            'requests_processed': 0,
            'requests_rejected': 0,
            'estimated_cost_saved': 0.0,
            'spam_blocked': 0,
            'duplicates_prevented': 0
        }

    def validate_and_optimize_request(self, 
                                    user_phone: str, 
                                    message: str, 
                                    request_type: str = 'simple_message',
                                    user_tier: str = 'free',
                                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive request validation and cost optimization
        
        Returns:
            Dict with processing decision, cost info, and user feedback
        """
        self.session_stats['requests_processed'] += 1
        
        try:
            # Step 1: Basic validation (free)
            if not self._basic_validation(user_phone, message):
                self.session_stats['requests_rejected'] += 1
                return self._create_rejection_response(
                    reason="invalid_input",
                    user_message="Please provide a valid phone number and message about nutrition or meal planning.",
                    cost_saved=0.01
                )
            
            # Step 2: Spam protection (low cost)
            spam_check = self.spam_protection.check_message_allowed(user_phone, message)
            if not spam_check.get('allowed', True):
                self.session_stats['spam_blocked'] += 1
                self.session_stats['requests_rejected'] += 1
                estimated_saved = self._estimate_processing_cost(request_type, message)
                self.session_stats['estimated_cost_saved'] += estimated_saved
                
                return self._create_rejection_response(
                    reason=f"spam_protection_{spam_check.get('reason', 'unknown')}",
                    user_message="Message blocked by spam protection. Please send legitimate nutrition-related questions.",
                    cost_saved=estimated_saved
                )
            
            # Step 3: Intelligent cost optimization
            optimization_result = optimize_request_cost(
                user_phone=user_phone,
                message=message,
                request_type=request_type,
                user_tier=user_tier
            )
            
            # Handle optimization decisions
            action = optimization_result.get('action')
            
            if action == 'reject':
                self.session_stats['requests_rejected'] += 1
                cost_saved = optimization_result.get('estimated_cost', 0.01)
                self.session_stats['estimated_cost_saved'] += cost_saved
                
                return self._create_rejection_response(
                    reason=optimization_result.get('reason'),
                    user_message=optimization_result.get('user_message', 
                        "Request optimized for cost efficiency. Please try a different nutrition question."),
                    cost_saved=cost_saved,
                    metadata=optimization_result.get('metadata', {})
                )
            
            elif action == 'throttle':
                self.session_stats['duplicates_prevented'] += 1
                return self._create_throttle_response(optimization_result)
            
            elif action == 'warn':
                return self._create_warning_response(optimization_result)
            
            elif action == 'premium_only':
                return self._create_premium_upsell_response(optimization_result)
            
            # Request approved for processing
            return self._create_approval_response(optimization_result, context)
            
        except Exception as e:
            logger.error(f"Error in cost-aware validation: {str(e)}")
            # Fail safe - allow processing but track error
            return {
                'should_process': True,
                'cost_optimized': False,
                'estimated_cost': 0.02,
                'user_message': None,
                'metadata': {'validation_error': str(e)},
                'optimization_applied': False
            }

    def _basic_validation(self, user_phone: str, message: str) -> bool:
        """Basic validation checks"""
        if not PhoneValidator.is_valid_phone(user_phone):
            return False
        
        if not MessageValidator.is_valid_message(message):
            return False
        
        return True

    def _estimate_processing_cost(self, request_type: str, message: str) -> float:
        """Estimate what processing this request would have cost"""
        base_costs = {
            'meal_plan': 0.05,
            'nutrition_analysis': 0.03,
            'recipe_search': 0.02,
            'grocery_list': 0.02,
            'dietary_advice': 0.04,
            'simple_message': 0.01
        }
        
        base_cost = base_costs.get(request_type, 0.02)
        
        # Adjust for message complexity
        if len(message.split()) > 50:
            base_cost *= 1.5
        
        return base_cost

    def _create_rejection_response(self, reason: str, user_message: str, cost_saved: float, metadata: Dict = None) -> Dict[str, Any]:
        """Create response for rejected requests"""
        return {
            'should_process': False,
            'cost_optimized': True,
            'reason': reason,
            'estimated_cost_saved': cost_saved,
            'user_message': user_message,
            'metadata': metadata or {},
            'optimization_applied': True,
            'cost_efficiency': 'high'  # Prevented wasteful spending
        }

    def _create_throttle_response(self, optimization_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create response for throttled requests"""
        return {
            'should_process': True,
            'cost_optimized': True,
            'reason': optimization_result.get('reason'),
            'estimated_cost': optimization_result.get('estimated_cost', 0.01),
            'user_message': optimization_result.get('user_message'),
            'metadata': optimization_result.get('metadata', {}),
            'optimization_applied': True,
            'processing_delay': 2,  # Add 2 second delay
            'cost_efficiency': 'medium'
        }

    def _create_warning_response(self, optimization_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create response for requests with warnings"""
        return {
            'should_process': True,
            'cost_optimized': True,
            'reason': optimization_result.get('reason'),
            'estimated_cost': optimization_result.get('estimated_cost'),
            'user_message': optimization_result.get('user_message'),
            'metadata': optimization_result.get('metadata', {}),
            'optimization_applied': True,
            'cost_efficiency': 'medium',
            'warning': True
        }

    def _create_premium_upsell_response(self, optimization_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create response for premium upsell situations"""
        upsell_message = (
            "🚀 You've reached your daily limit! Upgrade to Premium for:\n"
            "✅ Unlimited meal plans\n"
            "✅ Priority processing\n"
            "✅ Advanced nutrition analysis\n"
            "✅ Custom dietary recommendations\n\n"
            "Upgrade now for just $4.99/month!"
        )
        
        return {
            'should_process': False,
            'cost_optimized': True,
            'reason': optimization_result.get('reason'),
            'estimated_cost_saved': optimization_result.get('estimated_cost', 0.02),
            'user_message': upsell_message,
            'metadata': {
                'upsell_opportunity': True,
                'pricing': '$4.99/month',
                **optimization_result.get('metadata', {})
            },
            'optimization_applied': True,
            'cost_efficiency': 'high'
        }

    def _create_approval_response(self, optimization_result: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create response for approved requests"""
        return {
            'should_process': True,
            'cost_optimized': True,
            'estimated_cost': optimization_result.get('estimated_cost'),
            'user_message': None,  # No message needed for normal processing
            'metadata': {
                'confidence': optimization_result.get('confidence'),
                'optimization_reason': optimization_result.get('reason'),
                'context': context or {},
                **optimization_result.get('metadata', {})
            },
            'optimization_applied': True,
            'cost_efficiency': 'optimal'
        }

    def get_cost_savings_report(self) -> Dict[str, Any]:
        """Generate cost savings report for monitoring"""
        if self.session_stats['requests_processed'] == 0:
            return {'status': 'no_data'}
        
        rejection_rate = (self.session_stats['requests_rejected'] / self.session_stats['requests_processed']) * 100
        
        return {
            'session_stats': self.session_stats.copy(),
            'rejection_rate_percent': round(rejection_rate, 2),
            'estimated_monthly_savings': self.session_stats['estimated_cost_saved'] * 30,  # Rough estimate
            'efficiency_metrics': {
                'spam_prevention_rate': self.session_stats['spam_blocked'] / max(self.session_stats['requests_processed'], 1),
                'duplicate_prevention_rate': self.session_stats['duplicates_prevented'] / max(self.session_stats['requests_processed'], 1),
                'total_optimization_rate': self.session_stats['requests_rejected'] / max(self.session_stats['requests_processed'], 1)
            },
            'cost_categories': {
                'high_efficiency': self.session_stats['requests_rejected'],
                'medium_efficiency': self.session_stats['duplicates_prevented'],
                'optimal_processing': self.session_stats['requests_processed'] - self.session_stats['requests_rejected']
            }
        }

    def suggest_cost_optimizations(self, user_phone: str) -> Dict[str, Any]:
        """Suggest cost optimizations for a specific user"""
        try:
            # Get user's recent patterns
            daily_cost = self.cost_optimizer._get_user_daily_cost(user_phone, datetime.utcnow().strftime('%Y-%m-%d'))
            
            suggestions = []
            potential_savings = 0.0
            
            # Analyze patterns and suggest optimizations
            if daily_cost > 1.50:
                suggestions.append({
                    'type': 'usage_pattern',
                    'suggestion': 'Consider batching your nutrition questions to get more comprehensive answers',
                    'potential_savings': 0.50
                })
                potential_savings += 0.50
            
            if daily_cost > 1.00:
                suggestions.append({
                    'type': 'premium_upgrade',
                    'suggestion': 'Upgrade to Premium for better value and unlimited access',
                    'potential_savings': daily_cost - 4.99  # Monthly cost vs daily usage
                })
            
            suggestions.append({
                'type': 'efficiency_tip',
                'suggestion': 'Be specific in your questions for better, more cost-effective responses',
                'potential_savings': 0.20
            })
            
            return {
                'suggestions': suggestions,
                'total_potential_savings': potential_savings,
                'current_daily_cost': float(daily_cost),
                'optimization_opportunities': len(suggestions)
            }
            
        except Exception as e:
            logger.error(f"Error generating cost suggestions: {str(e)}")
            return {'error': 'Unable to generate suggestions at this time'}

# Integration helper functions

def process_nutrition_request_with_optimization(user_phone: str, 
                                              message: str, 
                                              request_type: str = 'simple_message',
                                              user_tier: str = 'free') -> Tuple[bool, Dict[str, Any]]:
    """
    Main integration function for processing nutrition requests with cost optimization
    
    Returns:
        Tuple of (should_process, optimization_info)
    """
    handler = CostAwareRequestHandler()
    result = handler.validate_and_optimize_request(
        user_phone=user_phone,
        message=message,
        request_type=request_type,
        user_tier=user_tier
    )
    
    should_process = result.get('should_process', False)
    
    # Log cost optimization metrics
    if result.get('cost_optimized'):
        logger.info(f"Cost optimization applied for {user_phone}: {result.get('reason', 'unknown')}")
        
        if result.get('estimated_cost_saved', 0) > 0:
            logger.info(f"Estimated cost saved: ${result.get('estimated_cost_saved'):.4f}")
    
    return should_process, result

def get_user_cost_recommendations(user_phone: str) -> Dict[str, Any]:
    """Get personalized cost optimization recommendations for a user"""
    handler = CostAwareRequestHandler()
    return handler.suggest_cost_optimizations(user_phone)

def generate_cost_efficiency_report() -> Dict[str, Any]:
    """Generate system-wide cost efficiency report"""
    handler = CostAwareRequestHandler()
    return handler.get_cost_savings_report()
