"""
Subscription Management Service
Handles user subscriptions, billing, and premium feature access.
Integrates with Stripe for payment processing.
"""

import boto3
import stripe
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from decimal import Decimal
import json

from packages.shared.datetime_utils import utc_now
logger = logging.getLogger(__name__)


class SubscriptionService:
    """Manages user subscriptions and premium features"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.ssm = boto3.client('ssm')
        
        # Get Stripe API key from Parameter Store
        try:
            stripe_key = self.ssm.get_parameter(
                Name='/ai-nutritionist/stripe/secret-key',
                WithDecryption=True
            )['Parameter']['Value']
            stripe.api_key = stripe_key
        except Exception as e:
            logger.error(f"Failed to get Stripe key: {e}")
            
        self.subscriptions_table = self.dynamodb.Table('ai-nutritionist-subscriptions')
        self.usage_table = self.dynamodb.Table('ai-nutritionist-usage')
        
    def get_subscription_status(self, user_phone: str) -> Dict[str, Any]:
        """Get user's subscription status and limits"""
        try:
            response = self.subscriptions_table.get_item(
                Key={'user_phone': user_phone}
            )
            
            if 'Item' not in response:
                # New user - return free tier
                return {
                    'tier': 'free',
                    'status': 'active',
                    'plan_limit': 3,
                    'plans_used_this_month': 0,
                    'premium_features': False,
                    'expires_at': None
                }
                
            subscription = response['Item']
            
            # Check if subscription is still valid
            if subscription.get('expires_at'):
                expires_at = datetime.fromisoformat(subscription['expires_at'])
                if expires_at < utc_now():
                    subscription['status'] = 'expired'
                    subscription['tier'] = 'free'
                    subscription['premium_features'] = False
                    
            return subscription
            
        except Exception as e:
            logger.error(f"Error getting subscription status: {e}")
            # Return safe defaults
            return {
                'tier': 'free',
                'status': 'active',
                'plan_limit': 3,
                'plans_used_this_month': 0,
                'premium_features': False
            }
    
    def check_usage_limit(self, user_phone: str) -> Dict[str, Any]:
        """Check if user can generate another meal plan"""
        subscription = self.get_subscription_status(user_phone)
        
        if subscription['tier'] in ['premium', 'enterprise']:
            return {
                'can_generate': True,
                'reason': 'unlimited_access',
                'plans_remaining': 'unlimited'
            }
            
        # Check monthly usage for free tier
        current_month = utc_now().strftime('%Y-%m')
        try:
            usage_response = self.usage_table.get_item(
                Key={
                    'user_phone': user_phone,
                    'month': current_month
                }
            )
            
            plans_used = 0
            if 'Item' in usage_response:
                plans_used = int(usage_response['Item'].get('plans_generated', 0))
                
            plan_limit = subscription.get('plan_limit', 3)
            plans_remaining = max(0, plan_limit - plans_used)
            
            return {
                'can_generate': plans_remaining > 0,
                'reason': 'usage_limit' if plans_remaining == 0 else 'within_limit',
                'plans_remaining': plans_remaining,
                'plans_used': plans_used,
                'plan_limit': plan_limit
            }
            
        except Exception as e:
            logger.error(f"Error checking usage limit: {e}")
            return {
                'can_generate': False,
                'reason': 'error',
                'plans_remaining': 0
            }
    
    def increment_usage(self, user_phone: str) -> bool:
        """Track meal plan generation for billing/limits"""
        current_month = utc_now().strftime('%Y-%m')
        
        try:
            self.usage_table.update_item(
                Key={
                    'user_phone': user_phone,
                    'month': current_month
                },
                UpdateExpression='ADD plans_generated :inc SET updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            return False
    
    def create_stripe_customer(self, user_phone: str, user_data: Dict) -> Optional[str]:
        """Create Stripe customer for user"""
        try:
            customer = stripe.Customer.create(
                metadata={
                    'user_phone': user_phone,
                    'source': 'ai_nutritionist'
                },
                description=f"AI Nutritionist user {user_phone}"
            )
            
            # Store customer ID in subscription table
            self.subscriptions_table.put_item(
                Item={
                    'user_phone': user_phone,
                    'stripe_customer_id': customer.id,
                    'tier': 'free',
                    'status': 'active',
                    'created_at': datetime.utcnow().isoformat(),
                    'plan_limit': 3,
                    'premium_features': False
                }
            )
            
            return customer.id
            
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {e}")
            return None
    
    def create_subscription(self, user_phone: str, price_id: str) -> Dict[str, Any]:
        """Create Stripe subscription for user"""
        try:
            subscription_data = self.get_subscription_status(user_phone)
            customer_id = subscription_data.get('stripe_customer_id')
            
            if not customer_id:
                customer_id = self.create_stripe_customer(user_phone, {})
                if not customer_id:
                    return {'success': False, 'error': 'Failed to create customer'}
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                metadata={
                    'user_phone': user_phone
                }
            )
            
            # Update local subscription record
            tier = 'premium' if 'premium' in price_id else 'enterprise'
            plan_limit = 999999 if tier == 'premium' else 999999  # Unlimited
            
            self.subscriptions_table.update_item(
                Key={'user_phone': user_phone},
                UpdateExpression='''
                    SET tier = :tier,
                        stripe_subscription_id = :sub_id,
                        #status = :status,
                        plan_limit = :limit,
                        premium_features = :premium,
                        updated_at = :timestamp
                ''',
                ExpressionAttributeNames={
                    '#status': 'status'  # 'status' is a reserved word
                },
                ExpressionAttributeValues={
                    ':tier': tier,
                    ':sub_id': subscription.id,
                    ':status': 'active',
                    ':limit': plan_limit,
                    ':premium': True,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
            
            return {
                'success': True,
                'subscription_id': subscription.id,
                'status': subscription.status,
                'tier': tier
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_webhook(self, event_type: str, event_data: Dict) -> bool:
        """Handle Stripe webhook events"""
        try:
            if event_type == 'customer.subscription.deleted':
                # Subscription cancelled
                subscription = event_data['object']
                user_phone = subscription['metadata'].get('user_phone')
                
                if user_phone:
                    self.subscriptions_table.update_item(
                        Key={'user_phone': user_phone},
                        UpdateExpression='''
                            SET tier = :tier,
                                #status = :status,
                                premium_features = :premium,
                                plan_limit = :limit,
                                updated_at = :timestamp
                        ''',
                        ExpressionAttributeNames={
                            '#status': 'status'
                        },
                        ExpressionAttributeValues={
                            ':tier': 'free',
                            ':status': 'cancelled',
                            ':premium': False,
                            ':limit': 3,
                            ':timestamp': datetime.utcnow().isoformat()
                        }
                    )
                    
            elif event_type == 'invoice.payment_failed':
                # Payment failed
                invoice = event_data['object']
                subscription_id = invoice.get('subscription')
                
                if subscription_id:
                    # Update subscription status
                    # In a real implementation, you'd query by subscription_id
                    pass
                    
            return True
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False
    
    def get_upgrade_message(self, user_phone: str) -> str:
        """Generate upgrade message for users hitting limits"""
        usage_info = self.check_usage_limit(user_phone)
        
        if usage_info['can_generate']:
            return ""
            
        return f"""
🎯 You've used all {usage_info.get('plan_limit', 3)} free meal plans this month!

✨ **Upgrade to Premium ($7.99/month):**
• Unlimited meal plans
• Custom dietary restrictions
• Grocery list optimization
• Family meal planning
• 24/7 nutrition chat

🏢 **Enterprise ($99/month):**
• Everything in Premium
• 10 seats + API access
• Advanced analytics
• Team/family accounts
• Calendar sync
• Priority support

Reply "UPGRADE" to get started! 💪

Your current plan helps support our mission to reduce food waste and support local farmers. 🌱
        """.strip()
    
    def get_pricing_info(self) -> str:
        """Return pricing information"""
        return """
🏷️ **AI Nutritionist Pricing**

🆓 **Free Plan** - $0/month
• 3 meal plans per month
• Basic nutrition advice
• WhatsApp support

⭐ **Premium Plan** - $4.99/month
• Unlimited meal plans
• Custom dietary restrictions
• Grocery list optimization
• Family meal planning
• Advanced nutrition chat

🏢 **Enterprise Plan** - $9.99/month
• Everything in Premium
• Google Calendar sync
• Multi-user accounts
• Advanced analytics
• Priority support
• Custom integrations

💚 **Social Impact**: Every Premium subscription funds 5 free plans for families in need and supports local farmers!

Reply "UPGRADE" to start your premium journey! 🚀
        """.strip()


def get_subscription_service() -> SubscriptionService:
    """Factory function to get subscription service instance"""
    return SubscriptionService()
