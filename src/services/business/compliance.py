"""
Premium Features Service - High-Value Revenue Generation
Implements subscription tiers, usage tracking, and premium AI features
"""

import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


class PremiumFeaturesService:
    """Manages premium features and revenue generation"""
    
    # Premium feature pricing (monthly)
    PREMIUM_TIERS = {
        'free': {
            'price': 0,
            'meal_plans_per_month': 3,
            'features': ['basic_plans', 'whatsapp_support'],
            'edamam_calls': 10,
            'ai_messages': 20
        },
        'premium': {
            'price': 9.99,
            'meal_plans_per_month': 50,
            'features': [
                'unlimited_plans', 'ai_nutritionist_chat', 'edamam_recipes',
                'nutrition_analysis', 'family_plans', 'calendar_sync'
            ],
            'edamam_calls': 500,
            'ai_messages': 200
        },
        'family': {
            'price': 14.99,
            'meal_plans_per_month': 100,
            'features': [
                'unlimited_plans', 'ai_nutritionist_chat', 'edamam_recipes',
                'nutrition_analysis', 'family_coordination', 'calendar_sync',
                'shopping_lists', 'meal_prep_optimization', 'voice_planning'
            ],
            'edamam_calls': 1000,
            'ai_messages': 500,
            'family_members': 6
        },
        'enterprise': {
            'price': 99.99,
            'meal_plans_per_month': 1000,
            'features': [
                'unlimited_plans', 'ai_nutritionist_chat', 'edamam_recipes',
                'nutrition_analysis', 'employee_wellness', 'analytics_dashboard',
                'white_label', 'api_access', 'priority_support'
            ],
            'edamam_calls': 10000,
            'ai_messages': 5000,
            'employees': 200
        }
    }
    
    # Revenue streams and commission rates
    REVENUE_STREAMS = {
        'affiliate_grocery': 0.15,      # 15% commission
        'affiliate_meal_kits': 0.20,    # 20% commission
        'affiliate_appliances': 0.08,   # 8% commission
        'affiliate_supplements': 0.25,  # 25% commission
        'local_marketplace': 0.08,      # 8% transaction fee
        'data_insights': {              # B2B data products
            'basic': 99.99,             # $99.99/month
            'premium': 199.99,          # $199.99/month
            'enterprise': 499.99        # $499.99/month
        }
    }
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.subscriptions_table = self.dynamodb.Table('ai-nutritionist-subscriptions')
        self.usage_table = self.dynamodb.Table('ai-nutritionist-usage')
        self.revenue_table = self.dynamodb.Table('ai-nutritionist-revenue')
        
    def check_premium_access(self, user_phone: str, feature: str) -> Dict[str, Any]:
        """Check if user has access to premium feature"""
        try:
            # Get user subscription
            response = self.subscriptions_table.get_item(
                Key={'user_phone': user_phone}
            )
            
            if 'Item' not in response:
                tier = 'free'
            else:
                subscription = response['Item']
                tier = subscription.get('tier', 'free')
                
                # Check if subscription is expired
                if subscription.get('expires_at'):
                    expires_at = datetime.fromisoformat(subscription['expires_at'])
                    if expires_at < datetime.utcnow():
                        tier = 'free'
            
            # Check feature access
            tier_features = self.PREMIUM_TIERS[tier]['features']
            has_access = feature in tier_features
            
            return {
                'has_access': has_access,
                'tier': tier,
                'feature': feature,
                'upgrade_required': not has_access,
                'suggested_tier': self._get_suggested_upgrade(feature) if not has_access else None
            }
            
        except Exception as e:
            logger.error(f"Error checking premium access: {e}")
            return {
                'has_access': False,
                'tier': 'free',
                'feature': feature,
                'upgrade_required': True,
                'error': str(e)
            }
    
    def track_revenue_event(self, event_type: str, user_phone: str, amount: float, 
                          metadata: Dict = None) -> bool:
        """Track revenue events for analytics"""
        try:
            event_id = f"{user_phone}_{event_type}_{int(datetime.utcnow().timestamp())}"
            
            self.revenue_table.put_item(
                Item={
                    'event_id': event_id,
                    'user_phone': user_phone,
                    'event_type': event_type,  # subscription, affiliate, marketplace, etc.
                    'amount': Decimal(str(amount)),
                    'timestamp': datetime.utcnow().isoformat(),
                    'metadata': metadata or {}
                }
            )
            
            logger.info(f"Revenue event tracked: {event_type} ${amount} for {user_phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking revenue event: {e}")
            return False
    
    def process_affiliate_commission(self, user_phone: str, partner: str, 
                                   order_value: float, commission_rate: float = None) -> Dict:
        """Process affiliate commission from partnerships"""
        try:
            if commission_rate is None:
                commission_rate = self.REVENUE_STREAMS.get(f'affiliate_{partner}', 0.10)
            
            commission = order_value * commission_rate
            
            # Track revenue
            self.track_revenue_event(
                'affiliate_commission',
                user_phone,
                commission,
                {
                    'partner': partner,
                    'order_value': order_value,
                    'commission_rate': commission_rate
                }
            )
            
            return {
                'success': True,
                'commission': commission,
                'partner': partner,
                'order_value': order_value,
                'commission_rate': commission_rate
            }
            
        except Exception as e:
            logger.error(f"Error processing affiliate commission: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_usage_analytics(self, user_phone: str) -> Dict[str, Any]:
        """Get user usage analytics for upselling"""
        try:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Get current month usage
            usage_response = self.usage_table.get_item(
                Key={
                    'user_phone': user_phone,
                    'month': current_month
                }
            )
            
            if 'Item' not in usage_response:
                usage = {
                    'meal_plans_generated': 0,
                    'edamam_calls': 0,
                    'ai_messages': 0
                }
            else:
                usage = usage_response['Item']
            
            # Get user subscription tier
            subscription = self.subscriptions_table.get_item(
                Key={'user_phone': user_phone}
            ).get('Item', {})
            
            tier = subscription.get('tier', 'free')
            limits = self.PREMIUM_TIERS[tier]
            
            # Calculate usage percentages
            analytics = {
                'tier': tier,
                'usage': {
                    'meal_plans': {
                        'used': int(usage.get('meal_plans_generated', 0)),
                        'limit': limits['meal_plans_per_month'],
                        'percentage': min(100, (int(usage.get('meal_plans_generated', 0)) / limits['meal_plans_per_month']) * 100)
                    },
                    'edamam_calls': {
                        'used': int(usage.get('edamam_calls', 0)),
                        'limit': limits['edamam_calls'],
                        'percentage': min(100, (int(usage.get('edamam_calls', 0)) / limits['edamam_calls']) * 100)
                    },
                    'ai_messages': {
                        'used': int(usage.get('ai_messages', 0)),
                        'limit': limits['ai_messages'],
                        'percentage': min(100, (int(usage.get('ai_messages', 0)) / limits['ai_messages']) * 100)
                    }
                },
                'upsell_recommendation': self._get_upsell_recommendation(usage, tier)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            return {'error': str(e)}
    
    def generate_upgrade_message(self, user_phone: str, feature: str) -> str:
        """Generate personalized upgrade message"""
        access_check = self.check_premium_access(user_phone, feature)
        
        if access_check['has_access']:
            return "✅ You already have access to this premium feature!"
        
        suggested_tier = access_check.get('suggested_tier', 'premium')
        tier_info = self.PREMIUM_TIERS[suggested_tier]
        
        feature_names = {
            'ai_nutritionist_chat': '🤖 Personal AI Nutritionist Chat',
            'edamam_recipes': '🍳 Advanced Recipe Search',
            'nutrition_analysis': '📊 Detailed Nutrition Analysis',
            'family_plans': '👨‍👩‍👧‍👦 Family Meal Coordination',
            'calendar_sync': '📅 Calendar Integration',
            'voice_planning': '🎤 Voice Meal Planning',
            'shopping_lists': '🛒 Smart Shopping Lists'
        }
        
        feature_name = feature_names.get(feature, feature.replace('_', ' ').title())
        
        message = f"""
🌟 *Upgrade to {suggested_tier.title()} Plan* 🌟

To access {feature_name}, upgrade to our {suggested_tier.title()} plan!

💰 *Just ${tier_info['price']}/month*

✨ *Premium Features Include:*
{''.join([f'\\n• {f.replace("_", " ").title()}' for f in tier_info['features'][:5]])}
{'\\n• And much more!' if len(tier_info['features']) > 5 else ''}

📱 *Upgrade now:* Reply 'UPGRADE {suggested_tier.upper()}' 

💝 *Special Offer:* First month 50% off!
""".strip()
        
        return message
    
    def _get_suggested_upgrade(self, feature: str) -> str:
        """Get minimum tier that includes the feature"""
        for tier_name, tier_info in self.PREMIUM_TIERS.items():
            if feature in tier_info['features']:
                return tier_name
        return 'premium'
    
    def _get_upsell_recommendation(self, usage: Dict, current_tier: str) -> Optional[Dict]:
        """Recommend upgrade based on usage patterns"""
        if current_tier == 'enterprise':
            return None
            
        # Check if user is hitting limits
        meal_plans_used = int(usage.get('meal_plans_generated', 0))
        edamam_calls_used = int(usage.get('edamam_calls', 0))
        ai_messages_used = int(usage.get('ai_messages', 0))
        
        current_limits = self.PREMIUM_TIERS[current_tier]
        
        # Calculate usage percentages
        meal_plans_pct = (meal_plans_used / current_limits['meal_plans_per_month']) * 100
        edamam_pct = (edamam_calls_used / current_limits['edamam_calls']) * 100
        ai_messages_pct = (ai_messages_used / current_limits['ai_messages']) * 100
        
        # Recommend upgrade if hitting 80%+ on any limit
        if max(meal_plans_pct, edamam_pct, ai_messages_pct) >= 80:
            next_tiers = ['free', 'premium', 'family', 'enterprise']
            current_index = next_tiers.index(current_tier)
            
            if current_index < len(next_tiers) - 1:
                suggested_tier = next_tiers[current_index + 1]
                return {
                    'suggested_tier': suggested_tier,
                    'reason': 'usage_limit',
                    'current_usage': max(meal_plans_pct, edamam_pct, ai_messages_pct),
                    'benefits': self.PREMIUM_TIERS[suggested_tier]['features']
                }
        
        return None
    
    def get_revenue_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get revenue analytics for business intelligence"""
        try:
            if not start_date:
                start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
            if not end_date:
                end_date = datetime.utcnow().isoformat()
            
            # Query revenue events in date range
            # This is a simplified version - in production you'd use DynamoDB GSI
            # with timestamp-based queries
            
            revenue_summary = {
                'period': f"{start_date} to {end_date}",
                'subscription_revenue': 0,
                'affiliate_revenue': 0,
                'marketplace_revenue': 0,
                'data_revenue': 0,
                'total_revenue': 0,
                'user_metrics': {
                    'free_users': 0,
                    'premium_users': 0,
                    'family_users': 0,
                    'enterprise_users': 0
                }
            }
            
            # In production, implement proper revenue aggregation
            logger.info(f"Revenue summary generated for {start_date} to {end_date}")
            
            return revenue_summary
            
        except Exception as e:
            logger.error(f"Error generating revenue summary: {e}")
            return {'error': str(e)}


class CostOptimizationService:
    """Implements cost reduction strategies"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.dynamodb = boto3.resource('dynamodb')
        self.cost_table = self.dynamodb.Table('ai-nutritionist-costs')
        
    def track_ai_cost(self, user_phone: str, model_used: str, tokens_consumed: int, 
                     estimated_cost: float) -> bool:
        """Track AI usage costs for optimization"""
        try:
            cost_entry = {
                'user_phone': user_phone,
                'timestamp': datetime.utcnow().isoformat(),
                'model_used': model_used,
                'tokens_consumed': tokens_consumed,
                'estimated_cost': Decimal(str(estimated_cost)),
                'month': datetime.utcnow().strftime('%Y-%m')
            }
            
            self.cost_table.put_item(Item=cost_entry)
            
            # Put metric to CloudWatch for monitoring
            self.cloudwatch.put_metric_data(
                Namespace='AInutritionist/Costs',
                MetricData=[
                    {
                        'MetricName': 'AI_Cost_Per_User',
                        'Value': estimated_cost,
                        'Unit': 'None',
                        'Dimensions': [
                            {
                                'Name': 'Model',
                                'Value': model_used
                            }
                        ]
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking AI cost: {e}")
            return False
    
    def get_cost_optimization_recommendations(self) -> List[Dict]:
        """Get AI-powered cost optimization recommendations"""
        recommendations = [
            {
                'category': 'AI Optimization',
                'recommendation': 'Implement response caching for common queries',
                'potential_savings': '70% reduction in AI costs',
                'implementation': 'Cache responses in DynamoDB with TTL'
            },
            {
                'category': 'Infrastructure',
                'recommendation': 'Use Reserved Instances for predictable workloads',
                'potential_savings': '40% EC2 cost reduction',
                'implementation': 'Purchase 1-year Reserved Instances'
            },
            {
                'category': 'API Optimization',
                'recommendation': 'Batch Edamam API calls',
                'potential_savings': '50% API cost reduction',
                'implementation': 'Group multiple nutrition queries'
            },
            {
                'category': 'Storage',
                'recommendation': 'Implement S3 Intelligent Tiering',
                'potential_savings': '30% storage cost reduction',
                'implementation': 'Auto-move old data to cheaper storage'
            }
        ]
        
        return recommendations
