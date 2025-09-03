"""
Enhanced Universal Message Handler with Triple Revenue Stream Integration
Handles messages while maximizing revenue through grocery affiliates, profit enforcement, and brand partnerships
"""

import json
import logging
import os
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

logger = logging.getLogger(__name__)


class RevenueOptimizedMessageHandler:
    """Message handler optimized for maximum revenue generation"""
    
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
    
    def handle_message(self, user_phone: str, message_text: str, 
                      context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle incoming message with revenue optimization"""
        try:
            # Step 1: Check profit enforcement BEFORE processing
            interaction_cost = self._estimate_interaction_cost(message_text)
            profit_check = self.profit_service.enforce_profit_policy(user_phone, interaction_cost)
            
            if not profit_check.get('allow_interaction', True):
                # Send payment required message
                response_text = profit_check['upgrade_message']
                return self._send_response(user_phone, response_text, {
                    'type': 'payment_required',
                    'payment_options': profit_check.get('payment_options', [])
                })
            
            # Step 2: Process the message
            if message_text.lower() in ['pay', 'payment', 'upgrade']:
                return self._handle_payment_request(user_phone)
            
            elif message_text.lower() in ['grocery', 'groceries', 'shopping']:
                return self._handle_grocery_request(user_phone, message_text)
            
            elif 'meal plan' in message_text.lower():
                return self._handle_meal_plan_request(user_phone, message_text, profit_check)
            
            else:
                return self._handle_general_ai_chat(user_phone, message_text, profit_check)
                
        except Exception as e:
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
