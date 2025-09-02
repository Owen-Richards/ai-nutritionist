"""
Profit-Enforced Message Handler
Integrates profit enforcement into every user interaction to guarantee $3+ profit per user monthly
"""

import json
import boto3
from typing import Dict, Any
from .user_cost_tracker import UserCostTracker
from .profit_enforcement_service import ProfitEnforcementService
from .ai_service import AIService
from .affiliate_revenue_service import AffiliateRevenueService

class ProfitEnforcedMessageHandler:
    def __init__(self):
        self.cost_tracker = UserCostTracker()
        self.profit_enforcer = ProfitEnforcementService()
        self.ai_service = AIService()
        self.affiliate_service = AffiliateRevenueService()

    def handle_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main message handler with profit enforcement
        """
        try:
            # Extract user and message info
            user_phone = self._extract_user_phone(event)
            message_text = self._extract_message_text(event)
            requested_action = self._classify_message_action(message_text)
            
            # Calculate estimated interaction cost
            estimated_cost = self._estimate_interaction_cost(requested_action, message_text)
            
            # Enforce profit requirements BEFORE processing
            enforcement_result = self.profit_enforcer.enforce_profit_requirements(
                user_phone=user_phone,
                requested_action=requested_action,
                interaction_cost=estimated_cost
            )
            
            # Handle different enforcement scenarios
            if not enforcement_result['action_allowed']:
                return self._handle_restricted_action(user_phone, enforcement_result)
            
            # Check if affiliate interaction required
            affiliate_check = self.profit_enforcer.check_affiliate_interaction_requirement(
                user_phone, requested_action
            )
            
            if affiliate_check['affiliate_required']:
                return self._handle_affiliate_requirement(user_phone, affiliate_check)
            
            # Process normal request with appropriate service level
            response = self._process_request_with_service_level(
                user_phone=user_phone,
                message_text=message_text,
                requested_action=requested_action,
                service_level=enforcement_result.get('restriction_level', 'normal'),
                enforcement_result=enforcement_result
            )
            
            # Track actual costs after processing
            actual_cost = self._calculate_actual_interaction_cost(response)
            self.cost_tracker.track_cost_event(
                user_phone=user_phone,
                event_type=f"{requested_action}_completed",
                cost_details={
                    'estimated_cost': estimated_cost,
                    'actual_cost': actual_cost,
                    'tokens_used': response.get('tokens_used', 0),
                    'service_level': enforcement_result.get('restriction_level', 'normal')
                },
                actual_cost=actual_cost
            )
            
            # Add upsell messages if appropriate
            response = self._add_upsell_opportunities(user_phone, response, enforcement_result)
            
            return response
            
        except Exception as e:
            return self._handle_error(e, user_phone if 'user_phone' in locals() else 'unknown')

    def _extract_user_phone(self, event: Dict) -> str:
        """Extract user phone number from webhook event"""
        # Handle different webhook formats
        if 'Body' in event:  # Twilio webhook
            body_params = event.get('Body', '')
            # Extract from Twilio format
            return event.get('From', '').replace('whatsapp:', '')
        elif 'user_phone' in event:  # Direct API call
            return event['user_phone']
        else:
            return 'unknown_user'

    def _extract_message_text(self, event: Dict) -> str:
        """Extract message text from webhook event"""
        if 'Body' in event:  # Twilio webhook
            return event.get('Body', '')
        elif 'message' in event:  # Direct API call
            return event['message']
        else:
            return ''

    def _classify_message_action(self, message_text: str) -> str:
        """Classify the type of action requested"""
        message_lower = message_text.lower()
        
        if any(word in message_lower for word in ['meal plan', 'menu', 'recipes', 'cook', 'dinner']):
            return 'meal_plan'
        elif any(word in message_lower for word in ['grocery', 'shopping', 'buy', 'ingredients']):
            return 'grocery_list'
        elif any(word in message_lower for word in ['nutrition', 'calories', 'healthy', 'diet']):
            return 'nutrition_analysis'
        elif any(word in message_lower for word in ['recipe', 'how to make', 'cooking']):
            return 'recipe_search'
        else:
            return 'simple_message'

    def _estimate_interaction_cost(self, action_type: str, message_text: str) -> float:
        """Estimate the cost of processing this interaction"""
        base_costs = {
            'simple_message': 0.01,      # Basic response
            'meal_plan': 0.08,           # AI generation + API calls
            'grocery_list': 0.04,        # Medium complexity
            'nutrition_analysis': 0.06,   # Analysis + data lookup
            'recipe_search': 0.03        # Search + formatting
        }
        
        # Add complexity factors
        base_cost = base_costs.get(action_type, 0.02)
        
        # Adjust for message length (longer = more processing)
        if len(message_text) > 100:
            base_cost *= 1.5
        
        # Add fixed costs (messaging, storage, etc.)
        fixed_costs = 0.01  # Twilio + DynamoDB + Lambda base costs
        
        return round(base_cost + fixed_costs, 4)

    def _handle_restricted_action(self, user_phone: str, enforcement_result: Dict) -> Dict:
        """Handle when action is not allowed due to profit enforcement"""
        enforcement_type = enforcement_result['enforcement_type']
        
        if enforcement_type == 'token_payment_required':
            return {
                'statusCode': 200,
                'body': self._format_twilio_response(enforcement_result['message']),
                'payment_required': True,
                'payment_url': enforcement_result.get('purchase_url'),
                'restriction_reason': 'insufficient_tokens'
            }
        
        elif enforcement_type == 'service_cutoff':
            return {
                'statusCode': 200,
                'body': self._format_twilio_response(enforcement_result['message']),
                'payment_required': True,
                'payment_url': enforcement_result.get('purchase_url'),
                'restriction_reason': 'cost_limit_exceeded'
            }
        
        else:
            return {
                'statusCode': 200,
                'body': self._format_twilio_response(
                    "Service temporarily unavailable. Please try again later."
                ),
                'restriction_reason': 'unknown_restriction'
            }

    def _handle_affiliate_requirement(self, user_phone: str, affiliate_check: Dict) -> Dict:
        """Handle when affiliate interaction is required"""
        affiliate_options = affiliate_check['affiliate_options']
        
        # Generate affiliate links
        affiliate_links = []
        for option in affiliate_options:
            link = self.affiliate_service.generate_affiliate_link(
                user_phone=user_phone,
                partner=option['name'].lower().replace(' ', '_'),
                product_context=option['category']
            )
            affiliate_links.append({
                'name': option['name'],
                'description': option['description'],
                'link': link['affiliate_url']
            })
        
        # Format response with affiliate options
        message = affiliate_check['message'] + "\n\n"
        for i, link_info in enumerate(affiliate_links, 1):
            message += f"{i}. {link_info['name']}: {link_info['description']}\n"
            message += f"   👆 {link_info['link']}\n\n"
        
        message += "After clicking any link above, send your message again for full AI assistance!"
        
        return {
            'statusCode': 200,
            'body': self._format_twilio_response(message),
            'affiliate_required': True,
            'affiliate_links': affiliate_links,
            'restriction_reason': 'affiliate_interaction_required'
        }

    def _process_request_with_service_level(self, user_phone: str, message_text: str, 
                                          requested_action: str, service_level: str,
                                          enforcement_result: Dict) -> Dict:
        """Process request according to allowed service level"""
        
        if service_level == 'affiliate_gated':
            # Return affiliate-focused response
            return {
                'statusCode': 200,
                'body': self._format_twilio_response(enforcement_result['message']),
                'service_level': 'affiliate_only',
                'affiliate_links': enforcement_result.get('affiliate_links', []),
                'tokens_used': 1  # Minimal token usage
            }
        
        elif service_level in ['reduced_quality', 'basic_only']:
            # Provide reduced AI service
            response = self._generate_reduced_quality_response(
                user_phone, message_text, requested_action, service_level
            )
            return {
                'statusCode': 200,
                'body': self._format_twilio_response(response['message']),
                'service_level': service_level,
                'tokens_used': response['tokens_used']
            }
        
        else:  # Normal service
            # Provide full AI service
            response = self._generate_full_quality_response(
                user_phone, message_text, requested_action
            )
            return {
                'statusCode': 200,
                'body': self._format_twilio_response(response['message']),
                'service_level': 'normal',
                'tokens_used': response['tokens_used']
            }

    def _generate_reduced_quality_response(self, user_phone: str, message_text: str, 
                                         action_type: str, service_level: str) -> Dict:
        """Generate reduced quality response to save costs"""
        if action_type == 'meal_plan':
            if service_level == 'basic_only':
                message = """🍽️ Basic Meal Ideas:
• Breakfast: Oatmeal with banana
• Lunch: Turkey sandwich with vegetables
• Dinner: Baked chicken with rice
• Snack: Apple with peanut butter

💎 Upgrade to Premium for personalized AI meal plans!"""
                tokens_used = 2
            else:
                # Use cached/template responses
                message = self._get_template_meal_plan()
                tokens_used = 3
        
        elif action_type == 'grocery_list':
            message = """🛒 Basic Shopping List:
• Proteins: Chicken, eggs, beans
• Vegetables: Broccoli, carrots, spinach
• Grains: Rice, bread, oats
• Fruits: Bananas, apples, berries

💎 Get personalized grocery lists with Premium!"""
            tokens_used = 2
        
        else:  # Simple message
            message = "Thanks for your message! For detailed responses, consider upgrading to Premium for unlimited AI assistance."
            tokens_used = 1
        
        return {
            'message': message,
            'tokens_used': tokens_used
        }

    def _generate_full_quality_response(self, user_phone: str, message_text: str, 
                                      action_type: str) -> Dict:
        """Generate full quality AI response"""
        try:
            # Use AI service for full response
            ai_response = self.ai_service.generate_response(
                user_phone=user_phone,
                message=message_text,
                context={'action_type': action_type}
            )
            
            return {
                'message': ai_response.get('response', 'AI service unavailable'),
                'tokens_used': ai_response.get('tokens_used', 5)
            }
            
        except Exception as e:
            # Fallback to template response
            return {
                'message': f"I understand you're asking about {action_type.replace('_', ' ')}. Let me help you with that! (AI temporarily unavailable)",
                'tokens_used': 2
            }

    def _get_template_meal_plan(self) -> str:
        """Get a template meal plan to reduce AI costs"""
        return """🍽️ Healthy Meal Plan:

**Breakfast:**
• Greek yogurt with berries and granola
• Green tea or coffee

**Lunch:**
• Grilled chicken salad with mixed vegetables
• Olive oil and lemon dressing

**Dinner:**
• Baked salmon with quinoa
• Steamed broccoli and carrots

**Snack:**
• Handful of almonds or apple slices

💎 Want personalized meal plans? Upgrade to Premium for AI-customized nutrition!"""

    def _calculate_actual_interaction_cost(self, response: Dict) -> float:
        """Calculate actual cost after processing"""
        base_cost = 0.01  # Fixed costs (messaging, storage)
        
        # Add costs based on service level
        service_level = response.get('service_level', 'normal')
        tokens_used = response.get('tokens_used', 1)
        
        if service_level == 'normal':
            ai_cost = tokens_used * 0.015  # Full AI cost
        elif service_level in ['reduced_quality', 'basic_only']:
            ai_cost = tokens_used * 0.005  # Reduced AI cost
        else:  # affiliate_only
            ai_cost = tokens_used * 0.001  # Minimal cost
        
        return round(base_cost + ai_cost, 4)

    def _add_upsell_opportunities(self, user_phone: str, response: Dict, 
                                enforcement_result: Dict) -> Dict:
        """Add appropriate upsell messages to response"""
        
        # Add upsell message if provided by enforcement
        if 'upsell_message' in enforcement_result:
            current_body = response['body']
            upsell_message = f"\n\n{enforcement_result['upsell_message']}"
            
            response['body'] = self._format_twilio_response(
                current_body.replace('</Response>', '') + upsell_message + '</Response>'
            )
        
        # Add token balance info for transparency
        token_balance = self.cost_tracker.get_user_token_balance(user_phone)
        if token_balance < 20:  # Low balance warning
            low_balance_message = f"\n\n🪙 Token balance: {token_balance} remaining"
            current_body = response['body']
            response['body'] = self._format_twilio_response(
                current_body.replace('</Response>', '') + low_balance_message + '</Response>'
            )
        
        return response

    def _format_twilio_response(self, message: str) -> str:
        """Format message for Twilio response"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""

    def _handle_error(self, error: Exception, user_phone: str) -> Dict:
        """Handle errors gracefully"""
        error_message = "Sorry, I'm experiencing technical difficulties. Please try again in a moment."
        
        # Track error cost (minimal)
        try:
            self.cost_tracker.track_cost_event(
                user_phone=user_phone,
                event_type='error_handling',
                cost_details={'error': str(error)},
                actual_cost=0.001
            )
        except:
            pass  # Don't let error tracking cause more errors
        
        return {
            'statusCode': 200,
            'body': self._format_twilio_response(error_message),
            'error': str(error)
        }

    def handle_payment_webhook(self, event: Dict) -> Dict:
        """Handle payment confirmation webhooks"""
        try:
            # Extract payment info
            user_phone = event.get('user_phone')
            payment_amount = float(event.get('amount', 0))
            payment_method = event.get('payment_method', 'stripe')
            
            # Process token purchase
            result = self.profit_enforcer.process_token_purchase(
                user_phone=user_phone,
                payment_amount=payment_amount,
                payment_method=payment_method
            )
            
            if result['purchase_successful']:
                # Send confirmation message
                confirmation_message = result['message']
                
                # Send via Twilio (you'd implement this)
                # self._send_whatsapp_message(user_phone, confirmation_message)
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'message': 'Payment processed successfully'
                    })
                }
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': result.get('error', 'Payment processing failed')
                    })
                }
                
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': str(e)
                })
            }

    def get_user_profitability_dashboard(self, user_phone: str) -> Dict:
        """Get profitability dashboard for a specific user"""
        profitability_status = self.cost_tracker.get_user_profitability_status(user_phone)
        token_balance = self.cost_tracker.get_user_token_balance(user_phone)
        
        return {
            'user_phone': user_phone[-4:] + '****',  # Privacy
            'profitability_status': profitability_status,
            'token_balance': token_balance,
            'recommendations': self._generate_user_recommendations(profitability_status),
            'dashboard_url': f'https://ai-nutritionist-dashboard.com/user/{user_phone}',
            'last_updated': datetime.utcnow().isoformat()
        }

    def _generate_user_recommendations(self, status: Dict) -> List[str]:
        """Generate recommendations for user based on profitability"""
        recommendations = []
        
        if status['monthly_profit'] < 3:
            recommendations.append("Consider purchasing tokens for unlimited access")
            recommendations.append("Check out our affiliate partners for exclusive discounts")
        
        if status['token_balance'] < 10:
            recommendations.append("Low token balance - consider purchasing more tokens")
        
        if status['monthly_revenue'] == 0:
            recommendations.append("Upgrade to Premium for enhanced features and unlimited access")
        
        return recommendations
