"""
Profit Enforcement Service
Implements guaranteed $3+ profit per user through token credits, service restrictions, and mandatory revenue streams
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from .cost_tracking import UserCostTracker
from .revenue import AffiliateRevenueService

class ProfitEnforcementService:
    def __init__(self):
        self.cost_tracker = UserCostTracker()
        self.affiliate_service = AffiliateRevenueService()
        self.dynamodb = boto3.resource('dynamodb')
        
        # Service restriction levels
        self.RESTRICTION_LEVELS = {
            'normal': {
                'ai_quality': 'high',
                'response_length': 'full',
                'features_available': 'all',
                'affiliate_required': False
            },
            'reduced_quality': {
                'ai_quality': 'medium',
                'response_length': 'medium',
                'features_available': 'basic',
                'affiliate_required': False
            },
            'basic_only': {
                'ai_quality': 'low',
                'response_length': 'short',
                'features_available': 'limited',
                'affiliate_required': False
            },
            'affiliate_gated': {
                'ai_quality': 'low',
                'response_length': 'affiliate_focused',
                'features_available': 'affiliate_only',
                'affiliate_required': True
            },
            'payment_required': {
                'ai_quality': 'none',
                'response_length': 'payment_prompt_only',
                'features_available': 'none',
                'affiliate_required': False
            }
        }

    def enforce_profit_requirements(self, user_phone: str, requested_action: str, 
                                  interaction_cost: float) -> Dict:
        """
        Main enforcement function - checks if action is allowed and enforces profit requirements
        """
        try:
            # Track the cost first
            cost_event = self.cost_tracker.track_cost_event(
                user_phone=user_phone,
                event_type=requested_action,
                cost_details={'interaction_cost': interaction_cost},
                actual_cost=interaction_cost
            )
            
            # Check token balance first
            token_check = self.cost_tracker.deduct_tokens(user_phone, requested_action)
            
            # If tokens insufficient, require payment
            if not token_check['action_allowed']:
                return self._generate_payment_requirement_response(user_phone, token_check)
            
            # Check if intervention needed based on costs
            intervention = cost_event.get('intervention_needed', {})
            
            # Apply appropriate enforcement based on intervention type
            if intervention['type'] == 'service_cutoff':
                return self._enforce_service_cutoff(user_phone)
            elif intervention['type'] == 'service_restriction':
                return self._enforce_service_restriction(user_phone, requested_action)
            elif intervention['type'] == 'cost_warning':
                return self._enforce_cost_warning(user_phone, requested_action)
            elif intervention['type'] == 'free_tier_exceeded':
                return self._enforce_premium_promotion(user_phone, requested_action)
            else:
                return self._allow_normal_service(user_phone, requested_action, token_check)
                
        except Exception as e:
            return {
                'action_allowed': False,
                'enforcement_type': 'error',
                'message': 'Service temporarily unavailable. Please try again.',
                'error': str(e)
            }

    def _generate_payment_requirement_response(self, user_phone: str, token_check: Dict) -> Dict:
        """Generate response requiring token purchase"""
        payment_amount = token_check.get('payment_amount', 5.00)
        
        return {
            'action_allowed': False,
            'enforcement_type': 'token_payment_required',
            'message': f'🪙 You need more tokens to continue!\n\n'
                      f'Required: {token_check["tokens_required"]} tokens\n'
                      f'Current balance: {token_check["current_balance"]} tokens\n\n'
                      f'💳 Purchase ${payment_amount:.2f} in tokens to continue unlimited access!\n'
                      f'👆 Tap here to buy tokens instantly',
            'payment_required': True,
            'payment_amount': payment_amount,
            'tokens_needed': token_check['tokens_required'],
            'current_balance': token_check['current_balance'],
            'purchase_url': f'https://ai-nutritionist-payments.com/tokens?user={user_phone}&amount={payment_amount}'
        }

    def _enforce_service_cutoff(self, user_phone: str) -> Dict:
        """Completely restrict service until payment"""
        profitability = self.cost_tracker.get_user_profitability_status(user_phone)
        required_payment = max(5.00, 3.00 - profitability['monthly_profit'])
        
        return {
            'action_allowed': False,
            'enforcement_type': 'service_cutoff',
            'message': f'🚫 Service temporarily suspended\n\n'
                      f'💰 Your monthly costs have exceeded our free tier limit.\n'
                      f'💳 Purchase ${required_payment:.2f} in tokens to restore full access!\n\n'
                      f'🎯 This one-time payment ensures unlimited access for the rest of the month.\n'
                      f'👆 Tap here to restore service',
            'payment_required': True,
            'payment_amount': required_payment,
            'restriction_level': 'payment_required',
            'purchase_url': f'https://ai-nutritionist-payments.com/restore?user={user_phone}&amount={required_payment}'
        }

    def _enforce_service_restriction(self, user_phone: str, requested_action: str) -> Dict:
        """Restrict service to affiliate-only responses"""
        # Generate affiliate recommendation instead of normal response
        affiliate_response = self._generate_affiliate_response(user_phone, requested_action)
        
        return {
            'action_allowed': True,
            'enforcement_type': 'affiliate_restriction',
            'message': affiliate_response['message'],
            'restricted_response': True,
            'restriction_level': 'affiliate_gated',
            'affiliate_links': affiliate_response['affiliate_links'],
            'unlock_message': '💎 Want personalized meal plans? Purchase tokens for full AI recommendations!'
        }

    def _enforce_cost_warning(self, user_phone: str, requested_action: str) -> Dict:
        """Provide normal service with upsell message"""
        return {
            'action_allowed': True,
            'enforcement_type': 'cost_warning',
            'upsell_message': '⚡ You\'re using our service actively! Purchase tokens for guaranteed unlimited access this month.',
            'restriction_level': 'normal',
            'token_purchase_incentive': 'Buy $5 in tokens and get 20% bonus tokens free!',
            'purchase_url': f'https://ai-nutritionist-payments.com/tokens?user={user_phone}&promo=bonus20'
        }

    def _enforce_premium_promotion(self, user_phone: str, requested_action: str) -> Dict:
        """Promote premium subscription"""
        return {
            'action_allowed': True,
            'enforcement_type': 'premium_promotion',
            'upsell_message': '🌟 Loving the meal plans? Upgrade to Premium for unlimited access + grocery lists!',
            'restriction_level': 'normal',
            'premium_benefits': [
                'Unlimited meal plans',
                'Automatic grocery lists', 
                'Family sharing for 6 people',
                'Premium recipe collections',
                'Priority customer support'
            ],
            'upgrade_url': f'https://ai-nutritionist-payments.com/premium?user={user_phone}'
        }

    def _allow_normal_service(self, user_phone: str, requested_action: str, token_check: Dict) -> Dict:
        """Allow normal service operation"""
        return {
            'action_allowed': True,
            'enforcement_type': 'normal_service',
            'restriction_level': 'normal',
            'tokens_remaining': token_check['remaining_balance'],
            'service_quality': 'high'
        }

    def _generate_affiliate_response(self, user_phone: str, requested_action: str) -> Dict:
        """Generate affiliate-focused response"""
        if requested_action == 'meal_plan':
            message = """🍽️ Here are some meal planning options:

🛒 **Meal Kit Delivery Services:**
• HelloFresh - Fresh ingredients + recipes delivered
• Blue Apron - Gourmet chef-designed meals
• Home Chef - Easy 30-minute meals

🥗 **Grocery Delivery:**
• Instacart - Same-day grocery delivery
• Amazon Fresh - Prime member benefits
• Walmart Grocery - Everyday low prices

📱 Tap any link above to get personalized recommendations + exclusive discounts!

💎 Want AI-powered personalized meal plans? Purchase tokens for full access!"""

            affiliate_links = self.affiliate_service.generate_contextual_affiliate_links(
                user_phone=user_phone,
                context="meal_planning",
                products=["meal_kits", "grocery_delivery"]
            )

        elif requested_action == 'grocery_list':
            message = """🛒 Smart Shopping Solutions:

📱 **Grocery Apps with Deals:**
• Instacart - Get groceries delivered in 1 hour
• Amazon Fresh - Subscribe & Save discounts
• Walmart+ - Free delivery on $35+ orders

🥬 **Healthy Food Specialists:**
• Thrive Market - Organic & natural foods
• iHerb - Supplements & health foods
• Whole Foods - Quality organic options

💰 Tap links for exclusive new customer discounts!

💎 Want AI-generated grocery lists? Purchase tokens for personalized shopping lists!"""

            affiliate_links = self.affiliate_service.generate_contextual_affiliate_links(
                user_phone=user_phone,
                context="grocery_shopping",
                products=["grocery_delivery", "health_foods"]
            )

        else:
            message = """🍎 Nutrition & Wellness Recommendations:

🌿 **Health & Supplements:**
• iHerb - Vitamins & natural supplements  
• Thrive Market - Organic pantry staples
• Amazon Health - Nutrition products

🍽️ **Meal Solutions:**
• HelloFresh - Balanced meal kits
• Blue Apron - Gourmet healthy options

💰 Exclusive discounts available through our partner links!

💎 Want personalized nutrition advice? Purchase tokens for AI-powered recommendations!"""

            affiliate_links = self.affiliate_service.generate_contextual_affiliate_links(
                user_phone=user_phone,
                context="nutrition",
                products=["supplements", "meal_kits"]
            )

        return {
            'message': message,
            'affiliate_links': affiliate_links
        }

    def process_token_purchase(self, user_phone: str, payment_amount: float, 
                             payment_method: str = 'stripe') -> Dict:
        """Process token purchase and update user balance"""
        try:
            # Calculate tokens purchased (20 tokens per $1)
            tokens_purchased = int(payment_amount * 20)
            
            # Apply bonus for larger purchases
            if payment_amount >= 10:
                bonus_tokens = int(tokens_purchased * 0.2)  # 20% bonus
                tokens_purchased += bonus_tokens
                bonus_message = f" + {bonus_tokens} bonus tokens!"
            else:
                bonus_message = ""
            
            # Update token balance
            current_balance = self.cost_tracker.get_user_token_balance(user_phone)
            new_balance = current_balance + tokens_purchased
            self.cost_tracker.set_user_token_balance(user_phone, new_balance)
            
            # Record revenue event
            self.cost_tracker.record_revenue_event(
                user_phone=user_phone,
                revenue_type='token_purchase',
                amount=payment_amount,
                details={
                    'tokens_purchased': tokens_purchased,
                    'payment_method': payment_method,
                    'bonus_applied': payment_amount >= 10
                }
            )
            
            return {
                'purchase_successful': True,
                'tokens_purchased': tokens_purchased,
                'new_balance': new_balance,
                'payment_amount': payment_amount,
                'message': f'🎉 Success! {tokens_purchased} tokens added to your account{bonus_message}\n\n'
                          f'💰 New balance: {new_balance} tokens\n'
                          f'🚀 You now have unlimited access for extended usage!',
                'service_restored': True
            }
            
        except Exception as e:
            return {
                'purchase_successful': False,
                'error': str(e),
                'message': 'Payment processing failed. Please try again or contact support.'
            }

    def check_affiliate_interaction_requirement(self, user_phone: str, requested_action: str) -> Dict:
        """Check if user needs to interact with affiliate links before service"""
        intervention = self.cost_tracker.check_intervention_needed(
            user_phone, 
            self.cost_tracker.get_monthly_cost(user_phone)
        )
        
        if intervention.get('require_affiliate_interaction', False):
            # Check if user has clicked affiliate links recently
            last_affiliate_click = self._get_last_affiliate_interaction(user_phone)
            
            if not last_affiliate_click or self._is_interaction_expired(last_affiliate_click):
                return {
                    'affiliate_required': True,
                    'message': '🛒 To continue, please check out our partner recommendations below!\n\n'
                              'This helps keep our service free. Choose any option that interests you:',
                    'required_clicks': 1 if requested_action == 'simple_message' else 2,
                    'affiliate_options': self._get_contextual_affiliate_options(requested_action)
                }
        
        return {
            'affiliate_required': False,
            'message': 'No affiliate interaction required'
        }

    def _get_last_affiliate_interaction(self, user_phone: str) -> Optional[datetime]:
        """Get timestamp of last affiliate link click"""
        # Implementation would check affiliate interaction tracking
        return None  # Placeholder

    def _is_interaction_expired(self, last_interaction: datetime) -> bool:
        """Check if affiliate interaction has expired (24 hours)"""
        from datetime import timedelta
        return datetime.utcnow() - last_interaction > timedelta(hours=24)

    def _get_contextual_affiliate_options(self, requested_action: str) -> List[Dict]:
        """Get affiliate options relevant to the requested action"""
        if requested_action in ['meal_plan', 'recipe_search']:
            return [
                {'name': 'HelloFresh', 'description': 'Get $40 off meal kits', 'category': 'meal_kits'},
                {'name': 'Instacart', 'description': 'Free delivery on first order', 'category': 'grocery'}
            ]
        elif requested_action in ['grocery_list', 'nutrition_analysis']:
            return [
                {'name': 'Thrive Market', 'description': '25% off organic foods', 'category': 'health_foods'},
                {'name': 'Amazon Fresh', 'description': '30-day free trial', 'category': 'grocery'}
            ]
        else:
            return [
                {'name': 'iHerb', 'description': '20% off supplements', 'category': 'supplements'},
                {'name': 'Walmart+', 'description': 'Free shipping + discounts', 'category': 'grocery'}
            ]

    def generate_profitability_report(self) -> Dict:
        """Generate comprehensive profitability report for all users"""
        try:
            all_users = self.cost_tracker.get_all_users_profitability()
            
            # Calculate aggregate metrics
            total_users = len(all_users)
            profitable_users = len([u for u in all_users if u['is_profitable']])
            total_revenue = sum(u['monthly_revenue'] for u in all_users)
            total_costs = sum(u['monthly_cost'] for u in all_users)
            total_profit = total_revenue - total_costs
            
            # Calculate average profit per user
            avg_profit_per_user = total_profit / total_users if total_users > 0 else 0
            
            # Identify users needing intervention
            users_needing_intervention = [u for u in all_users if u['needs_intervention']]
            
            return {
                'report_date': datetime.utcnow().isoformat(),
                'total_users': total_users,
                'profitable_users': profitable_users,
                'profitability_rate': (profitable_users / total_users * 100) if total_users > 0 else 0,
                'total_monthly_revenue': round(total_revenue, 2),
                'total_monthly_costs': round(total_costs, 2),
                'total_monthly_profit': round(total_profit, 2),
                'average_profit_per_user': round(avg_profit_per_user, 2),
                'users_needing_intervention': len(users_needing_intervention),
                'minimum_profit_guarantee': avg_profit_per_user >= 3.00,
                'intervention_users': [
                    {
                        'user_phone': u['user_phone'][-4:] + '****',  # Privacy
                        'monthly_profit': u['monthly_profit'],
                        'action_needed': 'payment_required' if u['monthly_profit'] < 0 else 'upsell_recommended'
                    }
                    for u in users_needing_intervention[:10]  # Top 10 for review
                ],
                'success_metrics': {
                    'users_above_3_profit': len([u for u in all_users if u['monthly_profit'] >= 3.00]),
                    'users_above_5_profit': len([u for u in all_users if u['monthly_profit'] >= 5.00]),
                    'users_above_10_profit': len([u for u in all_users if u['monthly_profit'] >= 10.00])
                }
            }
            
        except Exception as e:
            return {
                'report_date': datetime.utcnow().isoformat(),
                'error': str(e),
                'status': 'report_generation_failed'
            }
