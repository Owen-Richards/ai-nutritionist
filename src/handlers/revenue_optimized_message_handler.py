"""
Enhanced Universal Message Handler with Triple Revenue Stream Integration
Handles messages while maximizing revenue through grocery affiliates, profit enforcement, and brand partnerships
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import boto3

# Import enhanced services
from services.ai_service import AIService
from services.user_service import UserService
from services.meal_plan_service import MealPlanService
from services.aws_sms_service import AWSMessagingService
from services.affiliate_grocery_service import AffiliateGroceryService
from services.guaranteed_profit_service import ProfitEnforcementService
from services.brand_endorsement_service import BrandEndorsementService
from services.premium_features_service import PremiumFeaturesService

# Import improvement services
from services.performance_monitoring_service import PerformanceMonitoringService
from services.advanced_caching_service import AdvancedCachingService
from services.error_recovery_service import ErrorRecoveryService
from services.enhanced_user_experience_service import EnhancedUserExperienceService

logger = logging.getLogger(__name__)


class RevenueOptimizedMessageHandler:
    """Message handler optimized for maximum revenue generation with advanced improvements"""
    
    def __init__(self):
        # Initialize AWS clients
        self.dynamodb = boto3.resource('dynamodb')
        
        # Initialize core services
        self.user_service = UserService(self.dynamodb)
        self.ai_service = AIService()
        self.meal_plan_service = MealPlanService(self.dynamodb, self.ai_service)
        self.messaging_service = AWSMessagingService()
        
        # Initialize revenue services
        self.grocery_service = AffiliateGroceryService()
        self.profit_service = ProfitEnforcementService()
        self.brand_service = BrandEndorsementService()
        self.premium_service = PremiumFeaturesService()
        
        # Initialize improvement services
        self.performance_service = PerformanceMonitoringService()
        self.cache_service = AdvancedCachingService()
        self.error_service = ErrorRecoveryService()
        self.ux_service = EnhancedUserExperienceService()
    
    def handle_message(self, user_phone: str, message_text: str, 
                      context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle incoming message with revenue optimization and advanced improvements"""
        return self.error_service.execute_with_recovery(
            self._handle_message_internal, 
            'handle_message', 
            'general_response',
            user_phone, 
            message_text, 
            context
        )
    
    def _handle_message_internal(self, user_phone: str, message_text: str, 
                               context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Internal message handling with performance monitoring"""
        start_time = time.time()
        
        try:
            # Track user engagement
            self.ux_service.track_user_engagement(user_phone, 'message_received', {
                'message_length': len(message_text),
                'context': context or {}
            })
            
            # Check cache for similar responses first
            cache_key = f"response:{user_phone}:{hash(message_text)}"
            cached_response = self.cache_service.get_cached_data(cache_key, 'ai_response')
            
            if cached_response:
                self.performance_service.track_api_performance(
                    'handle_message', time.time() - start_time, True, 0.0, True
                )
                return cached_response
            
            # Get personalized response context
            personalized_context = self.ux_service.get_personalized_response(
                user_phone, message_text, context or {}
            )
            
            # Step 1: Check profit enforcement BEFORE processing
            interaction_cost = self._estimate_interaction_cost(message_text)
            profit_check = self.profit_service.enforce_profit_policy(user_phone, interaction_cost)
            
            if not profit_check.get('allow_interaction', True):
                # Send payment required message with personalized tone
                response_text = self._personalize_upgrade_message(
                    profit_check['upgrade_message'], personalized_context
                )
                response = self._send_response(user_phone, response_text, {
                    'type': 'payment_required',
                    'payment_options': profit_check.get('payment_options', []),
                    'personalization': personalized_context
                })
                
                # Cache the response
                self.cache_service.set_cached_data(cache_key, response, 'ai_response', 1)
                return response
            
            # Step 2: Process the message with intelligent routing
            response = None
            
            if message_text.lower() in ['pay', 'payment', 'upgrade']:
                response = self._handle_payment_request(user_phone, personalized_context)
            
            elif message_text.lower() in ['grocery', 'groceries', 'shopping']:
                response = self._handle_grocery_request(user_phone, message_text, personalized_context)
            
            elif 'meal plan' in message_text.lower():
                response = self._handle_meal_plan_request(user_phone, message_text, profit_check, personalized_context)
            
            else:
                response = self._handle_general_ai_chat(user_phone, message_text, profit_check, personalized_context)
            
            # Cache successful response
            if response and response.get('success', True):
                self.cache_service.set_cached_data(cache_key, response, 'ai_response', 6)  # 6 hour TTL
            
            # Track performance
            self.performance_service.track_api_performance(
                'handle_message', time.time() - start_time, True, interaction_cost, False
            )
            
            return response
                
        except Exception as e:
            # Performance tracking for errors
            self.performance_service.track_api_performance(
                'handle_message', time.time() - start_time, False, interaction_cost, False
            )
            
            logger.error(f"Error handling message: {str(e)}")
            return self._send_error_response(user_phone, str(e))
    
    def _handle_meal_plan_request(self, user_phone: str, message_text: str, 
                                profit_check: Dict) -> Dict[str, Any]:
        """Handle meal plan requests with maximum revenue optimization"""
        try:
            # Check if user can generate meal plans
            can_generate = self.premium_service.can_use_feature(user_phone, 'meal_plans')
            
            if not can_generate['allowed']:
                return self._send_response(user_phone, can_generate['upgrade_message'], {
                    'type': 'feature_limit',
                    'feature': 'meal_plans'
                })
            
            # Generate meal plan
            user_data = self.user_service.get_user(user_phone)
            meal_plan = self.meal_plan_service.generate_meal_plan(user_phone, user_data.get('preferences', {}))
            
            if not meal_plan.get('success', False):
                return self._send_error_response(user_phone, "Failed to generate meal plan")
            
            # Step 3: Enhance with brand integrations (Revenue Stream 3)
            enhanced_meal_plan = self.brand_service.integrate_brand_into_meal_plan(
                user_phone, meal_plan
            )
            
            # Step 4: Generate grocery list with affiliate links (Revenue Stream 1)
            grocery_result = self.grocery_service.generate_smart_grocery_list(
                enhanced_meal_plan, user_data.get('preferences', {})
            )
            
            # Step 5: Format response with revenue opportunities
            response_text = self._format_meal_plan_response(
                enhanced_meal_plan, grocery_result, user_phone
            )
            
            # Step 6: Track usage and revenue
            self._track_meal_plan_generation(user_phone, enhanced_meal_plan, grocery_result)
            
            # Step 7: Add profit warning if approaching limit
            if profit_check.get('warning'):
                response_text += f"\n\n{profit_check['upsell_message']}"
            
            return self._send_response(user_phone, response_text, {
                'type': 'meal_plan_with_revenue',
                'meal_plan': enhanced_meal_plan,
                'grocery_list': grocery_result,
                'revenue_generated': enhanced_meal_plan.get('brand_integrations', {}).get('total_revenue', 0)
            })
            
        except Exception as e:
            logger.error(f"Error handling meal plan request: {str(e)}")
            return self._send_error_response(user_phone, str(e))
    
    def _handle_grocery_request(self, user_phone: str, message_text: str) -> Dict[str, Any]:
        """Handle grocery-related requests with affiliate revenue focus"""
        try:
            user_data = self.user_service.get_user(user_phone)
            
            if 'schedule' in message_text.lower():
                return self._handle_grocery_scheduling(user_phone, message_text, user_data)
            else:
                return self._handle_grocery_list_request(user_phone, user_data)
                
        except Exception as e:
            logger.error(f"Error handling grocery request: {str(e)}")
            return self._send_error_response(user_phone, str(e))
    
    def _handle_grocery_scheduling(self, user_phone: str, message_text: str, 
                                 user_data: Dict) -> Dict[str, Any]:
        """Handle grocery delivery scheduling"""
        try:
            # Get latest meal plan
            latest_meal_plan = self.meal_plan_service.get_latest_meal_plan(user_phone)
            
            if not latest_meal_plan:
                response_text = (
                    "📋 *No meal plan found!*\n\n"
                    "Generate a meal plan first, then I'll help you schedule grocery delivery.\n\n"
                    "Reply 'meal plan' to get started! 🍽️"
                )
                return self._send_response(user_phone, response_text)
            
            # Generate grocery list
            grocery_result = self.grocery_service.generate_smart_grocery_list(
                latest_meal_plan, user_data.get('preferences', {})
            )
            
            if not grocery_result.get('success'):
                return self._send_error_response(user_phone, "Failed to generate grocery list")
            
            # Get delivery options
            delivery_options = grocery_result['delivery_options']
            
            response_text = (
                f"🛒 *Grocery Delivery Scheduling*\n\n"
                f"📦 Partner: {grocery_result['partner']['name']}\n"
                f"💰 Total: ${grocery_result['total_cost']:.2f}\n"
                f"💚 Savings: ${grocery_result['savings']:.2f}\n\n"
                f"📅 *Available Delivery Slots:*\n"
            )
            
            for i, option in enumerate(delivery_options[:6]):  # Show first 6 options
                fee_text = f" (+${option['fee']:.2f})" if option['fee'] > 0 else " (Free)"
                response_text += f"{i+1}. {option['date']} {option['time_slot']}{fee_text}\n"
            
            response_text += (
                f"\n🔗 Order now: {grocery_result['affiliate_link']}\n\n"
                f"💡 *Tip:* Ordering through our partner links helps keep this service free! 🙏"
            )
            
            # Track grocery list generation
            self._track_grocery_interaction(user_phone, grocery_result, 'list_generated')
            
            return self._send_response(user_phone, response_text, {
                'type': 'grocery_scheduling',
                'grocery_list': grocery_result
            })
            
        except Exception as e:
            logger.error(f"Error handling grocery scheduling: {str(e)}")
            return self._send_error_response(user_phone, str(e))
    
    def _handle_payment_request(self, user_phone: str) -> Dict[str, Any]:
        """Handle payment and upgrade requests"""
        try:
            # Get current profit status
            profit_status = self.profit_service.check_user_profitability(user_phone)
            payment_options = profit_status.get('payment_options', [])
            
            response_text = (
                f"💳 *Payment Options*\n\n"
                f"Current balance: ${profit_status['current_profit']:.2f}\n\n"
                f"*Quick Top-up Options:*\n"
            )
            
            for option in payment_options:
                recommended = " 🌟 *Recommended*" if option.get('recommended') else ""
                response_text += (
                    f"• ${option['amount']:.2f} → {option['tokens']} tokens{recommended}\n"
                    f"  {option['description']}\n\n"
                )
            
            response_text += (
                f"🛒 *Alternative:* Order groceries through our partners to earn credits!\n\n"
                f"💰 *Premium Plans:*\n"
                f"• Premium ($5/month): Unlimited everything\n"
                f"• Family ($15/month): 6 family members\n\n"
                f"Reply with the amount you'd like to pay (e.g., '$3') or 'premium' for subscription options."
            )
            
            return self._send_response(user_phone, response_text, {
                'type': 'payment_options',
                'payment_options': payment_options
            })
            
        except Exception as e:
            logger.error(f"Error handling payment request: {str(e)}")
            return self._send_error_response(user_phone, str(e))
    
    def _handle_general_ai_chat(self, user_phone: str, message_text: str, 
                              profit_check: Dict) -> Dict[str, Any]:
        """Handle general AI chat with cost optimization"""
        try:
            # Get AI response with cost consideration
            profit_status = profit_check.get('current_profit', 0)
            
            if profit_status < -0.25:  # Approaching warning threshold
                # Use cheaper, shorter responses
                ai_response = self.ai_service.get_quick_response(message_text)
            else:
                # Use full AI response
                ai_response = self.ai_service.get_ai_response(message_text, user_phone)
            
            # Add targeted brand recommendations
            brand_analysis = self.brand_service.analyze_user_for_targeting(user_phone)
            brand_ad = None
            
            if brand_analysis.get('brand_matches'):
                # Create subtle brand integration
                top_brand = list(brand_analysis['brand_matches'].keys())[0]
                brand_ad = self.brand_service.create_targeted_advertisement(
                    user_phone, top_brand, 'product_placement', ai_response
                )
            
            # Format response
            response_text = ai_response
            
            if brand_ad and brand_ad.get('success'):
                response_text += f"\n\n{brand_ad['ad_content']['content']}"
            
            # Add profit warning if needed
            if profit_check.get('warning'):
                response_text += f"\n\n{profit_check['upsell_message']}"
            
            # Track usage
            self._track_ai_interaction(user_phone, len(message_text), len(response_text))
            
            return self._send_response(user_phone, response_text, {
                'type': 'ai_chat',
                'brand_integration': brand_ad is not None
            })
            
        except Exception as e:
            logger.error(f"Error handling general AI chat: {str(e)}")
            return self._send_error_response(user_phone, str(e))
    
    def _format_meal_plan_response(self, meal_plan: Dict, grocery_result: Dict, 
                                 user_phone: str) -> str:
        """Format meal plan response with revenue optimizations"""
        try:
            response_text = "🍽️ *Your Personalized Weekly Meal Plan*\n\n"
            
            # Add meal plan summary
            weekly_plan = meal_plan.get('weekly_plan', {})
            for day, meals in weekly_plan.items():
                response_text += f"*{day.capitalize()}:*\n"
                for meal_type, meal in meals.items():
                    response_text += f"• {meal_type.title()}: {meal.get('name', 'Custom meal')}\n"
                    
                    # Add brand notes if present
                    if 'brand_notes' in meal:
                        for note in meal['brand_notes']:
                            response_text += f"  {note}\n"
                
                response_text += "\n"
            
            # Add grocery information
            if grocery_result.get('success'):
                response_text += (
                    f"🛒 *Smart Grocery List*\n"
                    f"📦 Partner: {grocery_result['partner']['name']}\n"
                    f"💰 Total: ${grocery_result['total_cost']:.2f}\n"
                    f"💚 You save: ${grocery_result['savings']:.2f}\n\n"
                    f"🔗 Order groceries: {grocery_result['affiliate_link']}\n\n"
                    f"📅 Reply 'schedule delivery' to plan your grocery delivery!\n\n"
                )
            
            # Add brand integration value
            brand_integrations = meal_plan.get('brand_integrations', {})
            if brand_integrations.get('total_revenue', 0) > 0:
                response_text += "💡 *Featured partner recommendations included to keep this service free!*\n\n"
            
            response_text += (
                f"💝 *What's next?*\n"
                f"• Reply 'grocery' for shopping list\n"
                f"• Reply 'schedule' for delivery planning\n"
                f"• Reply 'adjust' to modify preferences\n"
            )
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error formatting meal plan response: {str(e)}")
            return "✅ Meal plan generated! Check your plan details."
    
    def _estimate_interaction_cost(self, message_text: str) -> float:
        """Estimate the cost of processing this interaction"""
        base_cost = 0.01  # Base messaging cost
        
        if 'meal plan' in message_text.lower():
            base_cost += 0.15  # Meal plan generation cost
        
        if len(message_text) > 100:
            base_cost += 0.02  # Complex AI processing
        
        return base_cost
    
    def _track_meal_plan_generation(self, user_phone: str, meal_plan: Dict, 
                                  grocery_result: Dict):
        """Track meal plan generation for usage and revenue"""
        try:
            # Track usage
            self.premium_service.track_feature_usage(user_phone, 'meal_plans', 1)
            
            # Track revenue from brand integrations
            brand_revenue = meal_plan.get('brand_integrations', {}).get('total_revenue', 0)
            if brand_revenue > 0:
                self.premium_service.track_revenue_event(
                    'brand_integration', user_phone, brand_revenue
                )
            
            # Track grocery affiliate opportunity
            if grocery_result.get('success'):
                estimated_commission = grocery_result.get('estimated_commission', 0)
                if estimated_commission > 0:
                    self.premium_service.track_revenue_event(
                        'affiliate_opportunity', user_phone, estimated_commission
                    )
            
        except Exception as e:
            logger.error(f"Error tracking meal plan generation: {str(e)}")
    
    def _track_grocery_interaction(self, user_phone: str, grocery_result: Dict, 
                                 interaction_type: str):
        """Track grocery-related interactions"""
        try:
            estimated_commission = grocery_result.get('estimated_commission', 0)
            
            if estimated_commission > 0:
                self.premium_service.track_revenue_event(
                    f'grocery_{interaction_type}', user_phone, estimated_commission
                )
            
        except Exception as e:
            logger.error(f"Error tracking grocery interaction: {str(e)}")
    
    def _track_ai_interaction(self, user_phone: str, input_length: int, output_length: int):
        """Track AI interaction for cost monitoring"""
        try:
            # Estimate AI cost based on token usage
            estimated_cost = (input_length + output_length) * 0.00002  # Rough estimate
            
            self.premium_service.track_feature_usage(user_phone, 'ai_messages', 1)
            
        except Exception as e:
            logger.error(f"Error tracking AI interaction: {str(e)}")
    
    def _personalize_upgrade_message(self, base_message: str, 
                                   personalized_context: Dict[str, Any]) -> str:
        """Personalize upgrade message based on user context"""
        try:
            journey_stage = personalized_context.get('journey_stage', 'discovery')
            personalization_score = personalized_context.get('personalization_score', 0.0)
            
            if journey_stage == 'discovery':
                return f"🌟 {base_message} As a new user, you'll love our premium features!"
            elif journey_stage == 'engagement':
                return f"📈 {base_message} You're making great progress - unlock more with premium!"
            elif personalization_score > 0.7:
                return f"💪 {base_message} Based on your usage, premium will save you time and money!"
            else:
                return base_message
                
        except Exception as e:
            logger.error(f"Error personalizing upgrade message: {e}")
            return base_message
    
    def _handle_payment_request(self, user_phone: str, 
                              personalized_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment and upgrade requests with personalization"""
        try:
            # Track user engagement
            self.ux_service.track_user_engagement(user_phone, 'payment_request', {
                'journey_stage': personalized_context.get('journey_stage'),
                'personalization_score': personalized_context.get('personalization_score')
            })
            
            # Get personalized payment options
            payment_options = self.profit_service.get_payment_options(user_phone)
            
            # Customize message based on user journey
            journey_stage = personalized_context.get('journey_stage', 'discovery')
            
            if journey_stage == 'discovery':
                message = "🎯 Perfect timing! Let's get you started with premium features. Choose your plan:"
            elif journey_stage == 'engagement':
                message = "🚀 Ready to unlock everything? Here are your upgrade options:"
            else:
                message = "💎 Time to go premium! Select your preferred plan:"
            
            return self._send_response(user_phone, message, {
                'type': 'payment_options',
                'options': payment_options,
                'personalization': personalized_context
            })
            
        except Exception as e:
            logger.error(f"Error handling payment request: {e}")
            return self._send_error_response(user_phone, "Payment options temporarily unavailable")
    
    def _handle_grocery_request(self, user_phone: str, message_text: str,
                              personalized_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grocery requests with enhanced personalization"""
        try:
            # Track engagement
            self.ux_service.track_user_engagement(user_phone, 'grocery_request', {
                'message_text': message_text,
                'personalization': personalized_context
            })
            
            # Check cache for recent grocery requests
            cache_key = f"grocery:{user_phone}:{hash(message_text)}"
            cached_grocery = self.cache_service.get_cached_data(cache_key, 'grocery_prices')
            
            if cached_grocery:
                return cached_grocery
            
            # Get personalized grocery recommendations
            user_data = self.user_service.get_user(user_phone)
            preferences = user_data.get('preferences', {})
            
            # Get smart recommendations
            recommendations = self.ux_service.get_smart_recommendations(
                user_phone, 'grocery_shopping'
            )
            
            # Generate grocery list with affiliate opportunities
            grocery_result = self.grocery_service.generate_smart_grocery_list(
                user_phone, preferences, recommendations.get('meal_suggestions', [])
            )
            
            if grocery_result.get('success'):
                # Enhanced response with personalization
                response_text = self._format_grocery_response(
                    grocery_result, personalized_context
                )
                
                response = self._send_response(user_phone, response_text, {
                    'type': 'grocery_list',
                    'affiliate_links': grocery_result.get('affiliate_links', []),
                    'personalization': personalized_context
                })
                
                # Cache the result
                self.cache_service.set_cached_data(cache_key, response, 'grocery_prices', 4)
                
                return response
            else:
                return self._send_error_response(user_phone, "Unable to generate grocery list")
                
        except Exception as e:
            logger.error(f"Error handling grocery request: {e}")
            return self._send_error_response(user_phone, "Grocery service temporarily unavailable")
    
    def _handle_general_ai_chat(self, user_phone: str, message_text: str, 
                              profit_check: Dict, personalized_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general AI chat with enhanced personalization and cost optimization"""
        try:
            # Check cache for similar AI responses
            cache_key = f"ai_chat:{hash(message_text)}:{personalized_context.get('journey_stage')}"
            cached_response = self.cache_service.get_cached_data(cache_key, 'ai_response')
            
            if cached_response:
                return cached_response
            
            # Track engagement
            self.ux_service.track_user_engagement(user_phone, 'ai_chat', {
                'message_length': len(message_text),
                'journey_stage': personalized_context.get('journey_stage')
            })
            
            # Generate AI response with personalized context
            user_data = self.user_service.get_user(user_phone)
            
            # Use error recovery for AI service calls
            ai_response = self.error_service.execute_with_recovery(
                self.ai_service.generate_nutrition_response,
                'ai_chat',
                'ai_response',
                message_text,
                user_data.get('preferences', {}),
                personalized_context
            )
            
            if ai_response.get('success'):
                # Enhance response with brand integrations and smart suggestions
                enhanced_response = self._enhance_ai_response(
                    ai_response, user_phone, personalized_context
                )
                
                response = self._send_response(user_phone, enhanced_response['text'], {
                    'type': 'ai_chat',
                    'suggestions': enhanced_response.get('suggestions', []),
                    'brand_integrations': enhanced_response.get('brand_integrations', []),
                    'personalization': personalized_context
                })
                
                # Cache successful AI responses
                self.cache_service.set_cached_data(cache_key, response, 'ai_response', 6)
                
                return response
            else:
                return self._send_error_response(user_phone, "AI service temporarily unavailable")
                
        except Exception as e:
            logger.error(f"Error handling general AI chat: {e}")
            return self._send_error_response(user_phone, "Chat service temporarily unavailable")
    
    def _format_grocery_response(self, grocery_result: Dict, 
                               personalized_context: Dict[str, Any]) -> str:
        """Format grocery response with personalization"""
        try:
            base_response = grocery_result.get('message', '')
            journey_stage = personalized_context.get('journey_stage', 'discovery')
            
            if journey_stage == 'discovery':
                prefix = "🛒 Here's your personalized grocery list! "
            elif journey_stage == 'engagement':
                prefix = "📋 Your optimized shopping list is ready! "
            else:
                prefix = "🎯 Your premium grocery experience: "
            
            return f"{prefix}{base_response}"
            
        except Exception as e:
            logger.error(f"Error formatting grocery response: {e}")
            return grocery_result.get('message', 'Here is your grocery list')
    
    def _enhance_ai_response(self, ai_response: Dict, user_phone: str,
                           personalized_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance AI response with brand integrations and smart suggestions"""
        try:
            base_text = ai_response.get('text', '')
            
            # Add brand integrations if appropriate
            brand_integration = self.brand_service.get_contextual_brand_integration(
                user_phone, ai_response.get('context', {})
            )
            
            # Get smart follow-up suggestions
            suggestions = self.ux_service.get_smart_recommendations(
                user_phone, 'ai_chat_followup'
            )
            
            enhanced_text = base_text
            if brand_integration.get('success'):
                enhanced_text += f"\n\n💡 {brand_integration.get('message', '')}"
            
            return {
                'text': enhanced_text,
                'suggestions': suggestions.get('feature_suggestions', []),
                'brand_integrations': [brand_integration] if brand_integration.get('success') else [],
                'personalization_score': personalized_context.get('personalization_score', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error enhancing AI response: {e}")
            return {'text': ai_response.get('text', ''), 'suggestions': [], 'brand_integrations': []}
    
    def _handle_meal_plan_request(self, user_phone: str, message_text: str, 
                                profit_check: Dict, personalized_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle meal plan requests with enhanced personalization and caching"""
        try:
            # Check feature limits with personalized messaging
            can_generate = self.premium_service.can_use_feature(user_phone, 'meal_plans')
            
            if not can_generate['allowed']:
                personalized_upgrade = self._personalize_upgrade_message(
                    can_generate['upgrade_message'], personalized_context
                )
                return self._send_response(user_phone, personalized_upgrade, {
                    'type': 'feature_limit',
                    'feature': 'meal_plans',
                    'personalization': personalized_context
                })
            
            # Check cache for recent meal plans
            user_prefs_hash = hash(str(self.user_service.get_user(user_phone).get('preferences', {})))
            cache_key = f"meal_plan:{user_phone}:{user_prefs_hash}"
            cached_plan = self.cache_service.get_cached_data(cache_key, 'meal_plan')
            
            if cached_plan:
                # Update cached response with current personalization
                cached_plan['personalization'] = personalized_context
                return cached_plan
            
            # Track engagement
            self.ux_service.track_user_engagement(user_phone, 'meal_plan_request', {
                'message_text': message_text,
                'journey_stage': personalized_context.get('journey_stage')
            })
            
            # Generate personalized meal plan
            user_data = self.user_service.get_user(user_phone)
            
            # Use error recovery for meal plan generation
            meal_plan = self.error_service.execute_with_recovery(
                self.meal_plan_service.generate_meal_plan,
                'meal_plan_generation',
                'meal_plan',
                user_phone,
                user_data.get('preferences', {}),
                personalized_context
            )
            
            if not meal_plan.get('success', False):
                return self._send_error_response(user_phone, "Failed to generate meal plan")
            
            # Enhance with brand integrations and grocery affiliates
            enhanced_meal_plan = self.brand_service.integrate_brand_into_meal_plan(
                user_phone, meal_plan
            )
            
            # Generate grocery list with affiliate opportunities
            grocery_result = self.grocery_service.generate_grocery_list_from_meal_plan(
                user_phone, enhanced_meal_plan, curated_ordering=True
            )
            
            # Format comprehensive response
            response_text = self._format_meal_plan_response(
                enhanced_meal_plan, grocery_result, user_phone, personalized_context
            )
            
            response = self._send_response(user_phone, response_text, {
                'type': 'meal_plan',
                'meal_plan': enhanced_meal_plan,
                'grocery_links': grocery_result.get('affiliate_links', []),
                'personalization': personalized_context
            })
            
            # Cache the meal plan
            self.cache_service.set_cached_data(cache_key, response, 'meal_plan', 12)
            
            # Track revenue events
            self._track_meal_plan_generation(user_phone, enhanced_meal_plan, grocery_result)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling meal plan request: {e}")
            return self._send_error_response(user_phone, "Meal plan service temporarily unavailable")
    
    def _format_meal_plan_response(self, meal_plan: Dict, grocery_result: Dict, 
                                 user_phone: str, personalized_context: Dict[str, Any]) -> str:
        """Format meal plan response with enhanced personalization"""
        try:
            journey_stage = personalized_context.get('journey_stage', 'discovery')
            personalization_score = personalized_context.get('personalization_score', 0.0)
            
            # Personalized greeting
            if journey_stage == 'discovery':
                greeting = "🌟 Your first personalized meal plan is ready!"
            elif journey_stage == 'engagement':
                greeting = "🍽️ Another great meal plan, tailored just for you!"
            elif personalization_score > 0.8:
                greeting = "👨‍🍳 Your highly-personalized meal plan (we know you well!):"
            else:
                greeting = "🥗 Here's your custom meal plan:"
            
            base_response = meal_plan.get('formatted_response', '')
            
            # Add grocery integration if successful
            grocery_integration = ""
            if grocery_result.get('success'):
                commission_info = grocery_result.get('commission_info', {})
                if commission_info.get('total_savings', 0) > 0:
                    grocery_integration = f"\n\n🛒 Smart Shopping: Save ${commission_info['total_savings']:.2f} with our partner stores!"
            
            # Add personalized tips based on user journey
            personalized_tips = self._get_personalized_tips(user_phone, personalized_context)
            
            return f"{greeting}\n\n{base_response}{grocery_integration}\n\n{personalized_tips}"
            
        except Exception as e:
            logger.error(f"Error formatting meal plan response: {e}")
            return meal_plan.get('formatted_response', 'Here is your meal plan')
    
    def _get_personalized_tips(self, user_phone: str, 
                             personalized_context: Dict[str, Any]) -> str:
        """Get personalized tips based on user context"""
        try:
            journey_stage = personalized_context.get('journey_stage', 'discovery')
            
            tips = {
                'discovery': "💡 Tip: Save this plan and track your progress! Reply 'grocery' for a shopping list.",
                'engagement': "🎯 Pro tip: Premium users get unlimited meal plans and grocery delivery integration!",
                'optimization': "⚡ Advanced tip: Use voice commands or set up weekly meal plan automation.",
                'advocacy': "🌟 Share this with friends! They'll love our personalized nutrition approach."
            }
            
            return tips.get(journey_stage, tips['discovery'])
            
        except Exception as e:
            logger.error(f"Error getting personalized tips: {e}")
            return "💡 Tip: Save this plan and reply with questions anytime!"
    
    def _send_response(self, user_phone: str, response_text: str, 
                     metadata: Dict = None) -> Dict[str, Any]:
        """Send response message"""
        try:
            # Send via WhatsApp first, fallback to SMS
            whatsapp_result = self.messaging_service.send_whatsapp_message(
                user_phone, response_text
            )
            
            if whatsapp_result.get('success'):
                return {
                    'success': True,
                    'platform': 'whatsapp',
                    'message_sent': True,
                    'metadata': metadata
                }
            else:
                # Fallback to SMS
                sms_result = self.messaging_service.send_sms(user_phone, response_text)
                return {
                    'success': sms_result.get('success', False),
                    'platform': 'sms',
                    'message_sent': sms_result.get('success', False),
                    'metadata': metadata
                }
                
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_error_response(self, user_phone: str, error_message: str) -> Dict[str, Any]:
        """Send error response"""
        response_text = (
            "❌ *Oops! Something went wrong.*\n\n"
            "Please try again in a moment. If the issue persists, "
            "reply 'support' for help.\n\n"
            "💡 In the meantime, try:\n"
            "• 'meal plan' for weekly planning\n"
            "• 'grocery' for shopping lists\n"
            "• 'pay' for account options"
        )
        
        return self._send_response(user_phone, response_text, {
            'type': 'error',
            'error': error_message
        })


# Lambda handler for AWS integration
def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Lambda handler for revenue-optimized message processing"""
    try:
        handler = RevenueOptimizedMessageHandler()
        
        # Parse incoming message
        user_phone = event.get('user_phone')
        message_text = event.get('message')
        
        if not user_phone or not message_text:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing user_phone or message'})
            }
        
        # Process message
        result = handler.handle_message(user_phone, message_text, event)
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# Factory function
def get_revenue_optimized_handler():
    """Get RevenueOptimizedMessageHandler instance"""
    return RevenueOptimizedMessageHandler()
