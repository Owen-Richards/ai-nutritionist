"""
Guaranteed Profit Enforcement Service
Ensures every user generates minimum $1 profit per month through real-time monitoring
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import boto3

logger = logging.getLogger(__name__)


class ProfitEnforcementService:
    """Enforces guaranteed $1+ profit per user through progressive restrictions and payments"""
    
    # Profit thresholds and enforcement levels
    PROFIT_THRESHOLDS = {
        'warning': -0.50,      # Start upsells at 50¢ loss
        'restriction': -0.75,  # Reduce service quality at 75¢ loss
        'payment_required': -1.00,  # Require payment at $1 loss
        'service_suspension': -1.50  # Suspend service at $1.50 loss
    }
    
    # Payment options for profit restoration
    PAYMENT_TIERS = {
        'basic': {
            'amount': 1.00,
            'tokens': 20,
            'description': 'Basic service restoration',
            'profit_boost': 1.00
        },
        'standard': {
            'amount': 3.00,
            'tokens': 70,
            'description': 'Standard token package',
            'profit_boost': 3.00
        },
        'premium': {
            'amount': 5.00,
            'tokens': 120,
            'description': 'Premium token package',
            'profit_boost': 5.00
        },
        'power': {
            'amount': 10.00,
            'tokens': 250,
            'description': 'Power user package',
            'profit_boost': 10.00
        }
    }
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.ssm = boto3.client('ssm')
        
        # DynamoDB tables
        self.users_table = self.dynamodb.Table('ai-nutritionist-users')
        self.usage_table = self.dynamodb.Table('ai-nutritionist-usage-tracking')
        self.revenue_table = self.dynamodb.Table('ai-nutritionist-revenue-events')
        self.profit_table = self.dynamodb.Table('ai-nutritionist-profit-tracking')
    
    def check_user_profitability(self, user_phone: str) -> Dict[str, Any]:
        """Check user's current profitability status and enforce policies"""
        try:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Get user's monthly costs and revenue
            costs = self._get_monthly_costs(user_phone, current_month)
            revenue = self._get_monthly_revenue(user_phone, current_month)
            
            # Calculate current profit/loss
            current_profit = revenue - costs
            
            # Determine enforcement level
            enforcement_level = self._determine_enforcement_level(current_profit)
            
            # Get user's current status
            user_status = self._get_user_status(user_phone)
            
            result = {
                'user_phone': user_phone,
                'current_profit': float(current_profit),
                'monthly_costs': float(costs),
                'monthly_revenue': float(revenue),
                'enforcement_level': enforcement_level,
                'service_restrictions': self._get_service_restrictions(enforcement_level),
                'payment_options': self._get_payment_options(current_profit),
                'can_continue': enforcement_level != 'service_suspension',
                'requires_payment': enforcement_level in ['payment_required', 'service_suspension']
            }
            
            # Update profit tracking
            self._update_profit_tracking(user_phone, current_month, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking user profitability: {str(e)}")
            return {
                'user_phone': user_phone,
                'error': str(e),
                'can_continue': False,
                'requires_payment': True
            }
    
    def enforce_profit_policy(self, user_phone: str, interaction_cost: float) -> Dict[str, Any]:
        """Enforce profit policy before expensive operations"""
        try:
            # Check current profitability
            profit_status = self.check_user_profitability(user_phone)
            
            # Project profit after this interaction
            projected_profit = profit_status['current_profit'] - interaction_cost
            projected_enforcement = self._determine_enforcement_level(projected_profit)
            
            # If this interaction would trigger restrictions, intervene
            if projected_enforcement in ['payment_required', 'service_suspension']:
                return {
                    'allow_interaction': False,
                    'reason': 'profit_threshold_exceeded',
                    'current_profit': profit_status['current_profit'],
                    'projected_profit': projected_profit,
                    'interaction_cost': interaction_cost,
                    'payment_required': True,
                    'payment_options': self._get_payment_options(projected_profit),
                    'upgrade_message': self._generate_payment_required_message(user_phone, projected_profit)
                }
            
            # If approaching threshold, show warning
            elif projected_enforcement == 'restriction':
                return {
                    'allow_interaction': True,
                    'warning': True,
                    'reason': 'approaching_profit_limit',
                    'current_profit': profit_status['current_profit'],
                    'projected_profit': projected_profit,
                    'upsell_message': self._generate_upsell_message(user_phone, projected_profit),
                    'payment_options': self._get_payment_options(projected_profit)
                }
            
            # Normal operation
            return {
                'allow_interaction': True,
                'current_profit': profit_status['current_profit'],
                'projected_profit': projected_profit
            }
            
        except Exception as e:
            logger.error(f"Error enforcing profit policy: {str(e)}")
            return {
                'allow_interaction': False,
                'reason': 'system_error',
                'error': str(e)
            }
    
    def process_profit_payment(self, user_phone: str, payment_tier: str, 
                              payment_amount: float, payment_id: str) -> Dict[str, Any]:
        """Process payment to restore profitability"""
        try:
            if payment_tier not in self.PAYMENT_TIERS:
                return {'success': False, 'error': 'Invalid payment tier'}
            
            tier_config = self.PAYMENT_TIERS[payment_tier]
            
            # Validate payment amount
            if payment_amount < tier_config['amount']:
                return {'success': False, 'error': 'Insufficient payment amount'}
            
            # Record revenue event
            revenue_event = {
                'event_id': f"profit_payment_{user_phone}_{int(datetime.utcnow().timestamp())}",
                'user_phone': user_phone,
                'event_type': 'profit_payment',
                'payment_tier': payment_tier,
                'amount': Decimal(str(payment_amount)),
                'tokens_granted': tier_config['tokens'],
                'payment_id': payment_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.revenue_table.put_item(Item=revenue_event)
            
            # Update user's token balance
            self._add_user_tokens(user_phone, tier_config['tokens'])
            
            # Reset service restrictions
            self._reset_service_restrictions(user_phone)
            
            # Update monthly revenue
            current_month = datetime.utcnow().strftime('%Y-%m')
            self._add_monthly_revenue(user_phone, current_month, payment_amount, 'profit_payment')
            
            logger.info(f"Profit payment processed: ${payment_amount} from {user_phone}")
            
            return {
                'success': True,
                'payment_amount': payment_amount,
                'tokens_granted': tier_config['tokens'],
                'service_restored': True,
                'new_profit_status': self.check_user_profitability(user_phone)
            }
            
        except Exception as e:
            logger.error(f"Error processing profit payment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def generate_profit_enforcement_message(self, user_phone: str, 
                                          enforcement_level: str) -> str:
        """Generate user-friendly message about profit enforcement"""
        try:
            profit_status = self.check_user_profitability(user_phone)
            current_profit = profit_status['current_profit']
            
            if enforcement_level == 'warning':
                return (
                    f"💡 *Almost at your monthly usage limit!*\n\n"
                    f"You've used ${abs(current_profit):.2f} in AI services this month. "
                    f"To continue with full features:\n\n"
                    f"🎯 *Quick Top-up Options:*\n"
                    f"• $1 → 20 tokens (basic service)\n"
                    f"• $3 → 70 tokens (recommended)\n"
                    f"• $5 → 120 tokens (premium)\n\n"
                    f"Or generate revenue through grocery orders! 🛒"
                )
            
            elif enforcement_level == 'restriction':
                return (
                    f"⚠️ *Service Quality Reduced*\n\n"
                    f"Your account is ${abs(current_profit):.2f} over the free limit. "
                    f"Current service includes:\n"
                    f"• Basic meal suggestions ✅\n"
                    f"• Limited AI responses ⚡\n"
                    f"• No grocery lists ❌\n\n"
                    f"*Restore full service:*\n"
                    f"💳 Pay $1-10 for instant restoration\n"
                    f"🛒 Order groceries through our partners\n"
                    f"📱 Reply 'UPGRADE' for payment options"
                )
            
            elif enforcement_level == 'payment_required':
                return (
                    f"🚫 *Payment Required to Continue*\n\n"
                    f"Your account is ${abs(current_profit):.2f} over limit. "
                    f"To continue using the AI nutritionist:\n\n"
                    f"*Payment Options:*\n"
                    f"• $1 → Restore basic service\n"
                    f"• $3 → 70 tokens + full features\n"
                    f"• $5 → 120 tokens + premium perks\n\n"
                    f"*Alternative:* Order $30+ groceries through our partners "
                    f"to restore service immediately! 🛒\n\n"
                    f"Reply 'PAY' to see payment options"
                )
            
            elif enforcement_level == 'service_suspension':
                return (
                    f"⛔ *Service Temporarily Suspended*\n\n"
                    f"Account deficit: ${abs(current_profit):.2f}\n\n"
                    f"*Restore Service Options:*\n"
                    f"1️⃣ Pay $3+ to restore immediately\n"
                    f"2️⃣ Order groceries through our partners\n"
                    f"3️⃣ Upgrade to Premium ($5/month unlimited)\n\n"
                    f"We keep costs low by ensuring sustainable usage. "
                    f"Thanks for understanding! 🙏\n\n"
                    f"Reply 'RESTORE' for payment options"
                )
            
            else:
                return (
                    f"✅ *Account Status: Good*\n\n"
                    f"Current profit: ${current_profit:.2f}\n"
                    f"All services available!"
                )
                
        except Exception as e:
            logger.error(f"Error generating enforcement message: {str(e)}")
            return "Please contact support for account status information."
    
    def _get_monthly_costs(self, user_phone: str, month: str) -> Decimal:
        """Get user's total costs for the month"""
        try:
            response = self.usage_table.get_item(
                Key={
                    'user_phone': user_phone,
                    'month': month
                }
            )
            
            if 'Item' not in response:
                return Decimal('0.00')
            
            usage = response['Item']
            
            # Calculate costs based on usage
            costs = Decimal('0.00')
            
            # AI message costs
            ai_messages = int(usage.get('ai_messages', 0))
            costs += Decimal(str(ai_messages * 0.02))  # $0.02 per AI message
            
            # Meal plan generation costs
            meal_plans = int(usage.get('meal_plans_generated', 0))
            costs += Decimal(str(meal_plans * 0.15))  # $0.15 per meal plan
            
            # API calls (Edamam, etc.)
            api_calls = int(usage.get('edamam_calls', 0))
            costs += Decimal(str(api_calls * 0.005))  # $0.005 per API call
            
            # Messaging costs
            messages_sent = int(usage.get('messages_sent', 0))
            costs += Decimal(str(messages_sent * 0.0035))  # AWS messaging cost
            
            return costs
            
        except Exception as e:
            logger.error(f"Error getting monthly costs: {str(e)}")
            return Decimal('0.00')
    
    def _get_monthly_revenue(self, user_phone: str, month: str) -> Decimal:
        """Get user's total revenue contribution for the month"""
        try:
            # Query revenue events for this user and month
            response = self.revenue_table.scan(
                FilterExpression='user_phone = :phone AND begins_with(#ts, :month)',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':month': month
                }
            )
            
            total_revenue = Decimal('0.00')
            
            for item in response.get('Items', []):
                if 'amount' in item:
                    total_revenue += item['amount']
            
            return total_revenue
            
        except Exception as e:
            logger.error(f"Error getting monthly revenue: {str(e)}")
            return Decimal('0.00')
    
    def _determine_enforcement_level(self, current_profit: float) -> str:
        """Determine what enforcement level should be applied"""
        if current_profit >= 0:
            return 'normal'
        elif current_profit >= self.PROFIT_THRESHOLDS['warning']:
            return 'warning'
        elif current_profit >= self.PROFIT_THRESHOLDS['restriction']:
            return 'restriction'
        elif current_profit >= self.PROFIT_THRESHOLDS['payment_required']:
            return 'payment_required'
        else:
            return 'service_suspension'
    
    def _get_service_restrictions(self, enforcement_level: str) -> Dict[str, Any]:
        """Get service restrictions for enforcement level"""
        restrictions = {
            'normal': {
                'ai_quality': 'high',
                'grocery_lists': True,
                'meal_plans': True,
                'family_features': True,
                'priority_support': True
            },
            'warning': {
                'ai_quality': 'high',
                'grocery_lists': True,
                'meal_plans': True,
                'family_features': True,
                'priority_support': True,
                'show_upsells': True
            },
            'restriction': {
                'ai_quality': 'medium',
                'grocery_lists': False,
                'meal_plans': True,
                'family_features': False,
                'priority_support': False,
                'max_messages_per_day': 10
            },
            'payment_required': {
                'ai_quality': 'low',
                'grocery_lists': False,
                'meal_plans': False,
                'family_features': False,
                'priority_support': False,
                'max_messages_per_day': 3
            },
            'service_suspension': {
                'ai_quality': None,
                'grocery_lists': False,
                'meal_plans': False,
                'family_features': False,
                'priority_support': False,
                'max_messages_per_day': 0
            }
        }
        
        return restrictions.get(enforcement_level, restrictions['service_suspension'])
    
    def _get_payment_options(self, current_profit: float) -> List[Dict]:
        """Get payment options based on current deficit"""
        deficit = abs(current_profit) if current_profit < 0 else 0
        
        options = []
        
        for tier_id, config in self.PAYMENT_TIERS.items():
            if config['amount'] >= deficit:
                options.append({
                    'tier': tier_id,
                    'amount': config['amount'],
                    'tokens': config['tokens'],
                    'description': config['description'],
                    'recommended': config['amount'] == 3.00  # Standard tier
                })
        
        return options
    
    def _generate_payment_required_message(self, user_phone: str, projected_profit: float) -> str:
        """Generate payment required message"""
        deficit = abs(projected_profit)
        
        return (
            f"💳 *Payment Required*\n\n"
            f"This action would put your account ${deficit:.2f} over limit.\n\n"
            f"*Quick Payment Options:*\n"
            f"• $1 → Basic restoration\n"
            f"• $3 → Recommended (70 tokens)\n"
            f"• $5 → Premium (120 tokens)\n\n"
            f"Or order groceries through our partners! 🛒\n\n"
            f"Reply 'PAY' for instant payment links"
        )
    
    def _generate_upsell_message(self, user_phone: str, projected_profit: float) -> str:
        """Generate upsell message for approaching limits"""
        return (
            f"⚡ *Smart Tip: Top up now to avoid interruptions!*\n\n"
            f"You're close to your usage limit. Top up now:\n"
            f"• $3 → 70 tokens (most popular)\n"
            f"• $5 → 120 tokens + premium perks\n\n"
            f"Or earn credits through grocery orders! 🛒"
        )
    
    def _add_user_tokens(self, user_phone: str, tokens: int):
        """Add tokens to user's balance"""
        try:
            self.users_table.update_item(
                Key={'phone_number': user_phone},
                UpdateExpression='ADD token_balance :tokens',
                ExpressionAttributeValues={
                    ':tokens': tokens
                }
            )
        except Exception as e:
            logger.error(f"Error adding user tokens: {str(e)}")
    
    def _reset_service_restrictions(self, user_phone: str):
        """Reset any service restrictions for user"""
        try:
            self.users_table.update_item(
                Key={'phone_number': user_phone},
                UpdateExpression='REMOVE service_restrictions, enforcement_level',
                ExpressionAttributeValues={}
            )
        except Exception as e:
            logger.error(f"Error resetting service restrictions: {str(e)}")
    
    def _add_monthly_revenue(self, user_phone: str, month: str, amount: float, source: str):
        """Add revenue to user's monthly tracking"""
        try:
            self.users_table.update_item(
                Key={'phone_number': user_phone},
                UpdateExpression='ADD monthly_revenue.#month.#source :amount',
                ExpressionAttributeNames={
                    '#month': month,
                    '#source': source
                },
                ExpressionAttributeValues={
                    ':amount': Decimal(str(amount))
                }
            )
        except Exception as e:
            logger.error(f"Error adding monthly revenue: {str(e)}")
    
    def _get_user_status(self, user_phone: str) -> Dict:
        """Get user's current status"""
        try:
            response = self.users_table.get_item(
                Key={'phone_number': user_phone}
            )
            
            if 'Item' not in response:
                return {}
            
            return response['Item']
            
        except Exception as e:
            logger.error(f"Error getting user status: {str(e)}")
            return {}
    
    def _update_profit_tracking(self, user_phone: str, month: str, profit_data: Dict):
        """Update profit tracking table"""
        try:
            self.profit_table.put_item(
                Item={
                    'user_phone': user_phone,
                    'month': month,
                    'timestamp': datetime.utcnow().isoformat(),
                    'current_profit': Decimal(str(profit_data['current_profit'])),
                    'monthly_costs': Decimal(str(profit_data['monthly_costs'])),
                    'monthly_revenue': Decimal(str(profit_data['monthly_revenue'])),
                    'enforcement_level': profit_data['enforcement_level']
                }
            )
        except Exception as e:
            logger.error(f"Error updating profit tracking: {str(e)}")


# Factory function
def get_profit_enforcement_service():
    """Get ProfitEnforcementService instance"""
    return ProfitEnforcementService()
