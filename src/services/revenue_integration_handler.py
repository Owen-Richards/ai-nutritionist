"""
Revenue Integration Handler - Monetization Features for WhatsApp Bot
Integrates premium features, affiliate links, and upselling into the conversation flow
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

# Import our revenue services
from .premium_features_service import PremiumFeaturesService
from .affiliate_revenue_service import AffiliateRevenueService

logger = logging.getLogger(__name__)


class RevenueIntegrationHandler:
    """Handles monetization features in WhatsApp conversations"""
    
    def __init__(self):
        self.premium_service = PremiumFeaturesService()
        self.affiliate_service = AffiliateRevenueService()
        
        # Revenue trigger keywords
        self.upgrade_keywords = ['upgrade', 'premium', 'subscribe', 'unlock', 'pro']
        self.shopping_keywords = ['buy', 'shop', 'order', 'purchase', 'ingredients', 'grocery']
        
    def process_revenue_opportunity(self, user_phone: str, message: str, 
                                  meal_plan: Dict = None, user_profile: Dict = None) -> Dict[str, Any]:
        """Process potential revenue opportunities in user messages"""
        try:
            message_lower = message.lower()
            revenue_response = {
                'has_revenue_opportunity': False,
                'response_type': None,
                'response_message': '',
                'affiliate_links': [],
                'upgrade_suggestion': None
            }
            
            # Check if user is asking about premium features
            if any(keyword in message_lower for keyword in self.upgrade_keywords):
                return self._handle_upgrade_inquiry(user_phone, message, revenue_response)
            
            # Check if user wants to shop/order ingredients
            if any(keyword in message_lower for keyword in self.shopping_keywords):
                return self._handle_shopping_inquiry(user_phone, message, meal_plan, user_profile, revenue_response)
            
            # Check for premium feature usage that requires upgrade
            premium_check = self._check_premium_feature_usage(user_phone, message)
            if premium_check['requires_upgrade']:
                return self._handle_premium_gate(user_phone, premium_check['feature'], revenue_response)
            
            # Check if user is hitting usage limits (upselling opportunity)
            usage_check = self._check_usage_limits(user_phone)
            if usage_check['should_upsell']:
                return self._handle_usage_upsell(user_phone, usage_check, revenue_response)
            
            # Generate passive affiliate recommendations if meal plan exists
            if meal_plan:
                return self._generate_passive_recommendations(user_phone, meal_plan, user_profile, revenue_response)
            
            return revenue_response
            
        except Exception as e:
            logger.error(f"Error processing revenue opportunity: {e}")
            return {'has_revenue_opportunity': False, 'error': str(e)}
    
    def _handle_upgrade_inquiry(self, user_phone: str, message: str, response: Dict) -> Dict:
        """Handle direct upgrade inquiries"""
        response['has_revenue_opportunity'] = True
        response['response_type'] = 'upgrade_inquiry'
        
        # Get current subscription status
        subscription = self.premium_service.check_premium_access(user_phone, 'premium_plans')
        current_tier = subscription.get('tier', 'free')
        
        if current_tier == 'free':
            response['response_message'] = f"""
🌟 *Upgrade to Premium* 🌟

Unlock powerful features for just *$9.99/month*:

✨ *Premium Features:*
• 🤖 Personal AI Nutritionist Chat
• 🍳 Advanced Recipe Search (Edamam)
• 📊 Detailed Nutrition Analysis  
• 👨‍👩‍👧‍👦 Family Meal Coordination
• 📅 Calendar Integration
• 🛒 Smart Shopping Lists

💰 *Special Launch Offer:*
First month 50% off - Just $4.99!

📱 *Upgrade now:* Reply 'YES PREMIUM'
🤔 *Questions?* Reply 'PREMIUM INFO'

💝 *Bonus:* Every premium subscription funds 5 free plans for families in need!
""".strip()
        else:
            response['response_message'] = f"✅ You're already on our {current_tier.title()} plan! Enjoy all the premium features."
        
        return response
    
    def _handle_shopping_inquiry(self, user_phone: str, message: str, meal_plan: Dict, 
                               user_profile: Dict, response: Dict) -> Dict:
        """Handle shopping/ingredient purchase inquiries"""
        response['has_revenue_opportunity'] = True
        response['response_type'] = 'shopping_inquiry'
        
        if not meal_plan:
            response['response_message'] = "🛒 I'd love to help you shop! First, let me create a meal plan for you. What kind of meals are you interested in?"
            return response
        
        # Generate smart shopping recommendations
        recommendations = self.affiliate_service.get_smart_product_recommendations(
            meal_plan, user_profile
        )
        
        if recommendations:
            response['affiliate_links'] = recommendations
            
            # Create shopping response message
            grocery_rec = next((r for r in recommendations if r['type'] == 'grocery_delivery'), None)
            
            if grocery_rec:
                response['response_message'] = f"""
🛒 *Smart Shopping Options* 🛒

Based on your meal plan, here are the best ways to get your ingredients:

🚚 *{grocery_rec['title']}*
{grocery_rec['description']}
💰 {grocery_rec['estimated_savings']}

🔗 *Shop now:* {grocery_rec['url'][:50]}...

*Other options:*
""".strip()
                
                # Add other recommendations
                for rec in recommendations[1:3]:  # Show up to 2 more
                    response['response_message'] += f"\n• {rec['title']}"
                
                response['response_message'] += "\n\n💡 *Tip:* I earn a small commission when you shop through these links, which helps keep this service free!"
            
        else:
            response['response_message'] = "🛒 I'm working on getting grocery delivery partnerships in your area. For now, I can help you create a detailed shopping list!"
        
        return response
    
    def _handle_premium_gate(self, user_phone: str, feature: str, response: Dict) -> Dict:
        """Handle when user tries to access premium features"""
        response['has_revenue_opportunity'] = True
        response['response_type'] = 'premium_gate'
        
        upgrade_message = self.premium_service.generate_upgrade_message(user_phone, feature)
        response['response_message'] = upgrade_message
        response['upgrade_suggestion'] = {
            'required_feature': feature,
            'suggested_tier': 'premium',
            'price': 9.99
        }
        
        return response
    
    def _handle_usage_upsell(self, user_phone: str, usage_check: Dict, response: Dict) -> Dict:
        """Handle usage-based upselling"""
        response['has_revenue_opportunity'] = True
        response['response_type'] = 'usage_upsell'
        
        usage_analytics = self.premium_service.get_usage_analytics(user_phone)
        
        if usage_analytics.get('upsell_recommendation'):
            rec = usage_analytics['upsell_recommendation']
            suggested_tier = rec['suggested_tier']
            tier_info = self.premium_service.PREMIUM_TIERS[suggested_tier]
            
            response['response_message'] = f"""
📊 *You're a power user!* 📊

You've used {usage_check['percentage']:.0f}% of your monthly limits.

🚀 *Upgrade to {suggested_tier.title()}* for just *${tier_info['price']}/month*:

✨ *What you'll get:*
• {tier_info['meal_plans_per_month']} meal plans/month
• {tier_info['ai_messages']} AI messages/month  
• All premium features unlocked

💰 *Limited time:* 50% off first month!

📱 *Upgrade now:* Reply 'UPGRADE {suggested_tier.upper()}'
""".strip()
            
            response['upgrade_suggestion'] = {
                'current_usage': usage_check['percentage'],
                'suggested_tier': suggested_tier,
                'price': tier_info['price']
            }
        
        return response
    
    def _generate_passive_recommendations(self, user_phone: str, meal_plan: Dict, 
                                        user_profile: Dict, response: Dict) -> Dict:
        """Generate subtle affiliate recommendations"""
        # Only show passive recommendations occasionally (20% of the time)
        import random
        if random.random() > 0.2:
            return response
        
        recommendations = self.affiliate_service.get_smart_product_recommendations(
            meal_plan, user_profile
        )
        
        if recommendations:
            # Pick the highest priority recommendation
            top_rec = next((r for r in recommendations if r['priority'] == 'high'), 
                          recommendations[0] if recommendations else None)
            
            if top_rec:
                response['has_revenue_opportunity'] = True
                response['response_type'] = 'passive_recommendation'
                response['affiliate_links'] = [top_rec]
                
                response['response_message'] = f"""
💡 *Pro tip:* {top_rec['title']}

{top_rec['description']}
💰 {top_rec['estimated_savings']}

🔗 Interested? Reply 'SHOP' for the link!
""".strip()
        
        return response
    
    def _check_premium_feature_usage(self, user_phone: str, message: str) -> Dict:
        """Check if user is trying to use premium features"""
        premium_features_map = {
            'ai chat': 'ai_nutritionist_chat',
            'recipe search': 'edamam_recipes', 
            'nutrition analysis': 'nutrition_analysis',
            'family plan': 'family_plans',
            'calendar': 'calendar_sync',
            'shopping list': 'shopping_lists',
            'voice': 'voice_planning'
        }
        
        message_lower = message.lower()
        
        for trigger, feature in premium_features_map.items():
            if trigger in message_lower:
                access_check = self.premium_service.check_premium_access(user_phone, feature)
                if not access_check['has_access']:
                    return {
                        'requires_upgrade': True,
                        'feature': feature,
                        'trigger': trigger
                    }
        
        return {'requires_upgrade': False}
    
    def _check_usage_limits(self, user_phone: str) -> Dict:
        """Check if user is approaching usage limits"""
        analytics = self.premium_service.get_usage_analytics(user_phone)
        
        if analytics.get('upsell_recommendation'):
            # Calculate highest usage percentage
            usage = analytics['usage']
            max_percentage = max([
                usage['meal_plans']['percentage'],
                usage['edamam_calls']['percentage'], 
                usage['ai_messages']['percentage']
            ])
            
            return {
                'should_upsell': True,
                'percentage': max_percentage,
                'recommendation': analytics['upsell_recommendation']
            }
        
        return {'should_upsell': False}
    
    def process_upgrade_command(self, user_phone: str, command: str) -> Dict[str, Any]:
        """Process upgrade commands like 'YES PREMIUM', 'UPGRADE FAMILY'"""
        try:
            command_upper = command.upper()
            
            if 'YES PREMIUM' in command_upper or 'UPGRADE PREMIUM' in command_upper:
                return self._initiate_premium_upgrade(user_phone, 'premium')
            elif 'UPGRADE FAMILY' in command_upper:
                return self._initiate_premium_upgrade(user_phone, 'family')
            elif 'UPGRADE ENTERPRISE' in command_upper:
                return self._initiate_premium_upgrade(user_phone, 'enterprise')
            elif 'PREMIUM INFO' in command_upper:
                return self._provide_premium_info(user_phone)
            
            return {'handled': False}
            
        except Exception as e:
            logger.error(f"Error processing upgrade command: {e}")
            return {'handled': False, 'error': str(e)}
    
    def _initiate_premium_upgrade(self, user_phone: str, tier: str) -> Dict:
        """Initiate premium upgrade process"""
        tier_info = self.premium_service.PREMIUM_TIERS.get(tier, {})
        
        if not tier_info:
            return {
                'handled': True,
                'message': "❌ Invalid plan. Available plans: Premium ($9.99), Family ($14.99), Enterprise ($99.99)"
            }
        
        # Generate Stripe checkout link (placeholder)
        checkout_url = f"https://checkout.stripe.com/pay/ai-nutritionist-{tier}-{user_phone.replace('+', '')}"
        
        return {
            'handled': True,
            'message': f"""
🎉 *Starting {tier.title()} Upgrade* 🎉

💰 *Price:* ${tier_info['price']}/month
🎁 *Special offer:* 50% off first month!

🔐 *Secure checkout:* {checkout_url}

✨ *What you'll get:*
• {tier_info['meal_plans_per_month']} meal plans/month
• All premium features
• Priority support

💳 Complete your payment and start enjoying premium features immediately!

❓ Questions? Reply 'HELP UPGRADE'
""".strip()
        }
    
    def _provide_premium_info(self, user_phone: str) -> Dict:
        """Provide detailed premium information"""
        return {
            'handled': True,
            'message': """
ℹ️ *Premium Plan Details* ℹ️

🌟 *Premium ($9.99/month):*
• Unlimited meal plans
• AI nutritionist chat
• Advanced recipe search
• Nutrition analysis
• Family meal coordination  
• Calendar integration
• Smart shopping lists

👨‍👩‍👧‍👦 *Family ($14.99/month):*
• Everything in Premium
• Up to 6 family members
• Meal prep optimization
• Voice meal planning
• Bulk shopping coordination

🏢 *Enterprise ($99.99/month):*
• Everything in Family
• Employee wellness dashboard
• White-label options
• API access
• Priority support

💝 *Social Impact:* Every subscription funds 5 free meal plans for families in need!

📱 Ready to upgrade? Reply 'YES PREMIUM'
🤔 More questions? Just ask!
""".strip()
        }
    
    def get_revenue_metrics(self, user_phone: str) -> Dict:
        """Get revenue metrics for a specific user"""
        try:
            # Get subscription info
            subscription = self.premium_service.check_premium_access(user_phone, 'premium_plans')
            
            # Get usage analytics  
            usage = self.premium_service.get_usage_analytics(user_phone)
            
            # Get affiliate activity (would implement proper tracking)
            affiliate_activity = {
                'links_generated': 0,
                'purchases_made': 0,
                'total_commissions': 0
            }
            
            return {
                'user_phone': user_phone,
                'subscription_tier': subscription.get('tier', 'free'),
                'monthly_value': self.premium_service.PREMIUM_TIERS[subscription.get('tier', 'free')]['price'],
                'usage_analytics': usage,
                'affiliate_activity': affiliate_activity,
                'lifetime_value': 0,  # Would calculate based on subscription history
                'upgrade_probability': self._calculate_upgrade_probability(usage)
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue metrics: {e}")
            return {'error': str(e)}
    
    def _calculate_upgrade_probability(self, usage_analytics: Dict) -> float:
        """Calculate probability user will upgrade based on usage"""
        if not usage_analytics or 'usage' not in usage_analytics:
            return 0.1
        
        usage = usage_analytics['usage']
        
        # High usage indicates higher upgrade probability
        max_usage = max([
            usage['meal_plans']['percentage'],
            usage['edamam_calls']['percentage'],
            usage['ai_messages']['percentage']
        ])
        
        # Convert percentage to probability (80%+ usage = 70% upgrade probability)
        if max_usage >= 80:
            return 0.7
        elif max_usage >= 60:
            return 0.5
        elif max_usage >= 40:
            return 0.3
        else:
            return 0.1
