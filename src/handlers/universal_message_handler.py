"""
AI Nutritionist Assistant - Universal Message Handler
Handles incoming messages from any platform (WhatsApp, SMS, Telegram, Messenger, etc.)
Makes the AI feel like "just another contact" in your phone
WITH COMPREHENSIVE NUTRITION TRACKING AND BATTLE-TESTED UX
"""

import json
import logging
import os
import hashlib
import hmac
import base64
import random
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote, unquote_plus

import boto3
from botocore.exceptions import ClientError

# Import our domain-organized services with correct class names
from services.nutrition.insights import NutritionInsights
from services.nutrition.tracker import NutritionTracker
from services.personalization.preferences import UserPreferencesService
from services.personalization.goals import HealthGoalsService
from services.meal_planning.planner import MealPlanningService
from services.messaging.sms import SMSCommunicationService
from services.messaging.templates import MessageTemplatesService
from services.messaging.notifications import NotificationManagementService
from services.business.subscription import SubscriptionService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

# Initialize domain services using correct class names
user_preferences_service = UserPreferencesService(dynamodb)
nutrition_insights_service = NutritionInsights()
nutrition_tracker_service = NutritionTracker()
health_goals_service = HealthGoalsService()
meal_planning_service = MealPlanningService(dynamodb, nutrition_insights_service)
sms_communication_service = SMSCommunicationService()
message_templates_service = MessageTemplatesService()
notification_management_service = NotificationManagementService()
subscription_service = SubscriptionService()

# Compatibility aliases for existing code
user_service = user_preferences_service
messaging_service = sms_communication_service
nutrition_messaging_service = message_templates_service
consolidated_ai_service = nutrition_insights_service
meal_plan_service = meal_planning_service
multi_user_handler = notification_management_service


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Universal Lambda handler for processing messages from any platform
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Detect platform from event structure
        platform = messaging_service.detect_platform(event)
        if not platform:
            return create_error_response("Invalid platform")
        
        # Validate webhook signature for security
        if platform in ['whatsapp', 'sms']:
            signature = event.get('headers', {}).get('X-Twilio-Signature')
            if not messaging_service.verify_twilio_signature(signature, event.get('body', ''), reconstruct_url(event)):
                return create_error_response("Invalid signature", 403)
        
        # Extract message data
        message_data = messaging_service.extract_message_data(event, platform)
        if not message_data:
            return create_error_response("Invalid webhook format")
        
        # Process the message and generate response
        response_message = process_universal_message(message_data, platform)
        
        # Send response back to user
        success = send_response(message_data, response_message, platform)
        
        # Return appropriate response for platform
        return create_platform_response(platform, success)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return create_error_response("Internal server error", 500)


def process_universal_message(message_data: Dict[str, Any], platform: str) -> str:
    """
    Process message from any platform with nutrition tracking integration
    """
    try:
        user_id = message_data['user_id']
        user_message = message_data['message']
        phone_number = message_data.get('phone_number')
        
        logger.info(f"Processing message from {user_id}: {user_message}")
        
        # Get or create user profile
        user_profile = user_service.get_user_profile(user_id)
        if not user_profile:
            user_profile = user_service.create_user_profile({
                'user_id': user_id,
                'phone_number': phone_number,
                'platform': platform,
                'created_at': datetime.now().isoformat()
            })
        
        # Update interaction count and last seen
        user_service.update_user_interaction(user_id)
        
        # FIRST: Check for nutrition tracking patterns (most common usage)
        nutrition_response = nutrition_messaging_service.generate_contextual_response(user_message, user_id)
        if nutrition_response:
            return nutrition_response
        
        # Check subscription limits
        subscription_status = subscription_service.check_user_limits(user_id)
        if subscription_status['over_limit']:
            return create_upgrade_message(subscription_status, platform)
        
        # Process with seamless learning and adaptive conversation
        user_profile_obj = consolidated_ai_service.get_user_context(user_id) if hasattr(consolidated_ai_service, 'get_user_context') else user_profile
        response = handle_adaptive_conversation(user_message, user_profile, platform, None)
        
        # Track usage for billing
        subscription_service.track_usage(user_id, 'message_processed')
        
        # Format response to feel natural and friendly
        return messaging_service.format_friendly_message(response, platform)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return "Sorry, I'm having a bit of trouble right now. Mind trying that again? 😅"


def handle_adaptive_conversation(user_message: str, user_profile: Dict[str, Any], platform: str, special_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Handle conversation with full nutrition tracking and adaptive intelligence
    WITH PRIVACY-COMPLIANT MULTI-USER LINKING
    """
    message_lower = user_message.lower()
    user_id = user_profile['user_id']
    phone = user_profile.get('phone', '')
    
    # MULTI-USER LINKING COMMANDS (privacy-compliant GDPR)
    linking_result = multi_user_handler.handle_linking_message(user_id, phone, user_message)
    
    if linking_result.get("success") and linking_result.get("handled") != False:
        return linking_result["response"]
    
    # Check for pending actions (multi-step processes)
    pending_action = user_profile.get('pending_action')
    if pending_action:
        action_result = multi_user_handler.handle_action_followup(
            user_id, phone, user_message, pending_action
        )
        if action_result.get("success"):
            # Clear pending action if completed
            if action_result.get("delete_user"):
                # Special case: user requested complete deletion
                return action_result["response"]
            
            # Update user profile to clear pending action
            user_service.update_user(user_id, {'pending_action': None})
            return action_result["response"]
    
    # NUTRITION TRACKING COMMANDS (battle-tested patterns)
    
    # Stats and reports
    if any(word in message_lower for word in ['stats today', 'daily recap', 'how did i do']):
        return nutrition_messaging_service.format_daily_stats_response(user_profile['user_id'])
    
    elif any(word in message_lower for word in ['weekly report', 'week summary', 'weekly']):
        history = consolidated_ai_service.get_nutrition_history(user_profile['user_id'], days=7)
        if history.get('success'):
            return consolidated_ai_service._format_weekly_summary(history.get('history', []))
        return "I don't have enough nutrition data for a weekly report yet. Track some meals first!"
    
    elif 'macro breakdown' in message_lower or 'macros today' in message_lower:
        # Get today's nutrition data and format macro breakdown
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        history = consolidated_ai_service.get_nutrition_history(user_profile['user_id'], days=1)
        if history.get('success') and history.get('history'):
            today_data = history['history'][0]
            return f"""📊 *Today's Macros*
🥩 Protein: {today_data.get('protein', 0)}g
🍞 Carbs: {today_data.get('carbs', 0)}g  
🥑 Fat: {today_data.get('fat', 0)}g
🌾 Fiber: {today_data.get('fiber', 0)}g"""
        return "No macro data for today yet. Log some meals first!"
    
    elif 'fiber sources' in message_lower:
        return """🌾 *Great Fiber Sources*
• Raspberries: 8g per cup
• Lentils: 15g per cup  
• Chia seeds: 10g per 2 tbsp
• Artichokes: 10g per medium
• Black beans: 15g per cup
• Avocado: 10g per fruit"""
    
    elif 'sodium swaps' in message_lower or 'low sodium' in message_lower:
        return """🧂 *Smart Sodium Swaps*
• Lemon juice instead of salt
• Fresh herbs vs. seasoning packets
• Homemade broth vs. canned
• Garlic powder vs. garlic salt
• Fresh salsa vs. jarred
• Unsalted nuts vs. salted"""
    
    # Feeling better suggestions
    elif 'how can i feel better' in message_lower or 'feel better' in message_lower:
        return nutrition_messaging_service.format_how_can_i_feel_better_response(user_profile['user_id'])
    
    # Morning goal setting
    elif any(word in message_lower for word in ['morning', 'goals today', 'ready for today']):
        return nutrition_messaging_service.generate_morning_nudge(user_profile['user_id'])
    
    # ADAPTIVE MEAL PLANNING (with nutrition tracking integration)
    
    # Handle special contexts first
    if special_context:
        if special_context['type'] == 'dinner_party':
            return handle_dinner_party_planning(user_message, user_profile, special_context)
        elif special_context['type'] == 'travel':
            return handle_travel_planning(user_message, user_profile)
        elif special_context['type'] == 'recovery':
            return handle_recovery_planning(user_message, user_profile)
    
    # Greetings and casual conversation
    if any(word in message_lower for word in ['hi', 'hey', 'hello', 'morning', 'evening', 'good']):
        return create_adaptive_greeting(user_profile, platform)
    
    # Quick help or questions
    elif any(word in message_lower for word in ['help', 'what can you', 'what do you']):
        return create_adaptive_help_response(user_profile, platform)
    
    # Meal planning requests (use adaptive service)
    elif any(word in message_lower for word in ['meal plan', 'plan', 'recipe', 'menu', 'cook', 'eat']):
        return handle_adaptive_meal_planning(user_message, user_profile)
    
    # Grocery shopping requests
    elif any(word in message_lower for word in ['grocery', 'shopping', 'list', 'buy', 'store']):
        return handle_adaptive_grocery_list(user_profile)
    
    # Nutrition questions with modern science integration
    elif any(word in message_lower for word in ['nutrition', 'healthy', 'calories', 'protein', 'vitamin']):
        return handle_adaptive_nutrition_question(user_message, user_profile)
    
    # Strategy questions (IF, gut health, plant-forward, anti-inflammatory)
    elif 'intermittent fasting' in message_lower or 'time restricted' in message_lower:
        return nutrition_messaging_service.generate_strategy_suggestions(user_profile['user_id'], 'intermittent_fasting')
    
    elif any(word in message_lower for word in ['gut health', 'probiotics', 'fermented']):
        return nutrition_messaging_service.generate_strategy_suggestions(user_profile['user_id'], 'gut_friendly')
    
    elif 'plant forward' in message_lower or 'plant based' in message_lower:
        return nutrition_messaging_service.generate_strategy_suggestions(user_profile['user_id'], 'plant_forward')
    
    # Feedback processing (ratings, emoji reactions)
    elif any(word in message_lower for word in ['loved it', 'hated it', 'too spicy', 'bland', 'perfect']):
        return handle_meal_feedback_response(user_message, user_profile)
    
    # Subscription/upgrade inquiries
    elif any(word in message_lower for word in ['upgrade', 'premium', 'subscription', 'plan', 'price']):
        return create_subscription_info(platform)
    
    # Default: treat as general nutrition question with learning
    else:
        # Use consolidated AI service for nutrition advice
        return f"I'm here to help with nutrition questions! Could you be more specific about what you'd like to know? I can help with meal planning, nutrition analysis, or health tips. 🥗"


def handle_adaptive_meal_planning(user_message: str, user_profile: Dict[str, Any]) -> str:
    """Generate meal plan using consolidated AI service with modern nutrition strategies"""
    try:
        # Use consolidated AI service for meal planning
        meal_plan = consolidated_ai_service.generate_meal_plan(user_profile)
        
        if meal_plan:
            # Get personalized intro
            intro = meal_plan.get('personalized_intro', "Here's your personalized meal plan! 🍽️")
            
            # Format the meal plan
            formatted_plan = meal_plan_service.format_meal_plan_message(meal_plan)
            
            # Add strategy nudge if present
            strategy_nudge = meal_plan.get('strategy_nudge')
            if strategy_nudge:
                formatted_plan += f"\n\n💡 {strategy_nudge['message']}"
            
            # Add contextual tips
            tips = meal_plan.get('contextual_tips', [])
            if tips:
                formatted_plan += "\n\n" + "\n".join(tips)
            
            return f"{intro}\n\n{formatted_plan}\n\nLet me know how these work for you! Your feedback helps me get better! 😊"
        
        else:
            return "I'm having a little trouble putting together your meal plan right now. Can you try asking again in just a moment? 🤔"
            
    except Exception as e:
        logger.error(f"Error handling adaptive meal planning: {e}")
        return "Oops! Something went wrong while I was planning your meals. Mind trying again? 😅"


def handle_adaptive_grocery_list(user_profile: Dict[str, Any]) -> str:
    """Generate adaptive grocery list from recent meal plans"""
    try:
        # Get recent meal plans
        recent_plans = user_service.get_recent_meal_plans(user_profile['user_id'])
        
        if recent_plans:
            # Generate grocery list based on the most recent meal plan
            ingredients = []
            for day in recent_plans[-1].get('days', {}).values():
                for meal in day.values():
                    if isinstance(meal, dict) and 'recipe_data' in meal:
                        recipe_ingredients = meal['recipe_data'].get('ingredients', [])
                        ingredients.extend(recipe_ingredients)
            
            # Create a simple grocery list
            if ingredients:
                grocery_list = "\n".join([f"• {ingredient}" for ingredient in ingredients[:15]])  # Limit to 15 items
            else:
                grocery_list = "• Fresh vegetables\n• Lean proteins\n• Whole grains\n• Healthy fats"
            
            formatted_list = f"🛒 *Grocery List*\n{grocery_list}"
            
            # Add budget-conscious tips if user is price-sensitive
            budget_sensitivity = user_profile.get('budget_envelope', {}).get('price_sensitivity')
            if budget_sensitivity == 'high':
                formatted_list += "\n\n💰 Pro tip: Shop sales on produce and buy pantry staples in bulk!"
            
            return f"Perfect! Here's your shopping list based on your recent meal plan:\n\n{formatted_list}\n\nHappy shopping! 🛒"
        
        else:
            return "I'd love to make you a grocery list! First, let me create a meal plan for you. Just ask me for a 'meal plan' and I'll get you set up! 📋"
            
    except Exception as e:
        logger.error(f"Error handling adaptive grocery list: {e}")
        return "Having trouble with your grocery list right now. Try asking for a meal plan first? 🛒"


def handle_adaptive_nutrition_question(user_message: str, user_profile: Dict[str, Any]) -> str:
    """Handle nutrition questions with modern science and user context"""
    try:
        # Use consolidated AI service for nutrition advice
        advice = f"That's a great nutrition question! Let me help you with that. For specific nutrition advice, I recommend tracking your meals first so I can give you personalized recommendations. 🥗"
        
        # Add modern nutrition insights based on user interests
        strategies = user_profile.get('health_goals', {}).get('preferred_strategies', {})
        message_lower = user_message.lower()
        
        modern_insights = []
        
        # Add intermittent fasting context if relevant
        if strategies.get('intermittent_fasting') and any(word in message_lower for word in ['breakfast', 'meal timing', 'eating schedule']):
            modern_insights.append("💡 Since you're doing intermittent fasting, consider timing your eating window around your most active hours!")
        
        # Add gut health context if relevant
        if strategies.get('gut_health_focus') and any(word in message_lower for word in ['digestion', 'bloating', 'gut', 'probiotics']):
            modern_insights.append("🦠 For gut health, try adding fermented foods like kimchi or kefir - they're game-changers!")
        
        # Add plant-forward context if relevant  
        if strategies.get('plant_forward') and any(word in message_lower for word in ['protein', 'meat', 'plant']):
            modern_insights.append("🌱 Plant proteins like lentils and chickpeas can be just as satisfying and often easier to digest!")
        
        # Add anti-inflammatory context if relevant
        if strategies.get('anti_inflammatory') and any(word in message_lower for word in ['inflammation', 'pain', 'joints']):
            modern_insights.append("🔥 Anti-inflammatory foods like turmeric, olive oil, and fatty fish can really help with inflammation!")
        
        # Combine advice with modern insights
        if modern_insights:
            advice += "\n\n" + "\n\n".join(modern_insights)
        
        return advice
        
    except Exception as e:
        logger.error(f"Error handling adaptive nutrition question: {e}")
        return "That's a great nutrition question! I'm having a bit of trouble right now, but try asking me again in a moment? 🤔"


def create_adaptive_greeting(user_profile: Dict[str, Any], platform: str) -> str:
    """Create personalized greeting based on user learning"""
    interaction_count = user_profile.get('interaction_count', 0)
    learning_stage = user_profile.get('learning_stage', 'discovery')
    
    if interaction_count <= 3:
        # New user - warm welcome
        return create_welcome_message(platform)
    
    elif learning_stage == 'discovery':
        responses = [
            "Hey there! 😊 Good to see you again! Ready to discover some new flavors?",
            "Hi! Hope you're having a great day! What sounds good for meals this week?",
            "Hello! 👋 I'm still learning your tastes - what are you in the mood for?"
        ]
    
    elif learning_stage == 'preference_mapping':
        responses = [
            "Hey! 😊 I'm getting a better sense of what you love - excited to plan something perfect!",
            "Hi there! Ready for some meals tailored to your tastes?",
            "Hello! I've been learning your preferences - let's create something amazing! ✨"
        ]
    
    else:  # optimization stage
        taste_profile = user_profile.get('taste_profile', {})
        hero_ingredients = taste_profile.get('ingredient_heroes', [])
        
        if hero_ingredients:
            responses = [
                f"Hey! 😊 Ready for some meals with your favorites: {', '.join(hero_ingredients[:2])}?",
                "Hi! I know exactly what you love now - let's create your perfect week! 🎯",
                "Hello! Time for another perfectly dialed-in meal plan! ⭐"
            ]
        else:
            responses = [
                "Hey! 😊 Ready for meals perfectly matched to your taste? 🎯",
                "Hi there! Let's create another week of your ideal flavors! ✨"
            ]
    
    return random.choice(responses)


def create_adaptive_help_response(user_profile: Dict[str, Any], platform: str) -> str:
    """Create help response adapted to user's experience level"""
    interaction_count = user_profile.get('interaction_count', 0)
    
    if interaction_count <= 3:
        return create_help_response(platform)
    
    # Experienced user - show advanced features
    strategies = user_profile.get('health_goals', {}).get('preferred_strategies', {})
    active_strategies = [k for k, v in strategies.items() if v]
    
    response = """I'm here to make nutrition easy and delicious! Here's what I can do:

🍽️ **Adaptive Meal Plans** - I learn your tastes and create perfect plans
📊 **Nutrition Tracking** - Daily stats, weekly reports, macro breakdowns
📋 **Smart Grocery Lists** - Organized by store layout
💡 **Modern Nutrition Coaching** - IF, gut health, plant-forward, anti-inflammatory"""
    
    if active_strategies:
        response += f"\n🎯 **Your Active Strategies**: {', '.join(active_strategies)}"
    
    response += "\n\n**Quick Commands:**\n"
    response += "• 'stats today' - daily nutrition recap\n"
    response += "• 'weekly report' - comprehensive week summary\n"
    response += "• 'how can I feel better?' - personalized suggestions\n"
    response += "• Track meals: 'ate [meal]', 'skipped lunch', etc.\n"
    response += "• Track water: '2 cups water', '16 oz', etc.\n"
    
    response += "\n\nJust message me naturally - I understand context and remember our conversations! 😊"
    
    return response


def handle_meal_feedback_response(user_message: str, user_profile: Dict[str, Any]) -> str:
    """Handle feedback about meals intelligently"""
    message_lower = user_message.lower()
    
    if any(word in message_lower for word in ['loved', 'amazing', 'perfect', 'delicious']):
        responses = [
            "So happy you loved it! 🎉 I'll definitely remember what made this one special!",
            "Yes! That's exactly what I was hoping for! ⭐ More like this coming up!",
            "Perfect! I'm learning what makes you happy - this is gold! 💎"
        ]
    
    elif any(word in message_lower for word in ['hated', 'awful', 'terrible', 'disgusting']):
        responses = [
            "Good to know! Thanks for the honest feedback - I'll steer away from that style! 👍",
            "Noted! I'm still learning your preferences - this helps a lot! 📝",
            "Got it! Every 'no' gets me closer to your perfect 'yes'! ✅"
        ]
    
    elif any(word in message_lower for word in ['too spicy', 'too hot']):
        responses = [
            "Thanks! I'll dial back the heat for you - finding your perfect spice level! 🌶️",
            "Good feedback! I'm learning your spice tolerance - will adjust! 👍"
        ]
    
    elif any(word in message_lower for word in ['bland', 'boring', 'no flavor']):
        responses = [
            "Got it! I'll amp up the flavors next time - thanks for telling me! 🔥",
            "Perfect feedback! I'll bring more exciting flavors your way! ✨"
        ]
    
    else:
        responses = [
            "Thanks for the feedback! Every bit helps me get better at this! 👍",
            "Good to know! I'm always learning and improving! 📈"
        ]
    
    return random.choice(responses)


def handle_dinner_party_planning(user_message: str, user_profile: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Handle dinner party planning with contextual questions"""
    return """Perfect! I love helping with dinner parties! 🎉

Let me ask a few quick questions to make this amazing:

🍽️ How many guests will you have?
🎭 Casual get-together or more formal dinner?
🥗 Any dietary restrictions I should know about?
⏰ How much prep time do you want to spend?

Once I know these details, I'll create a fantastic menu with timeline and shopping list! ✨"""


def handle_travel_planning(user_message: str, user_profile: Dict[str, Any]) -> str:
    """Handle travel meal planning"""
    return """Ah, travel mode! I've got you covered! ✈️

I'll focus on:
🥪 Minimal prep meals
🏨 Hotel/Airbnb friendly options  
🥜 Portable snacks
🛒 Easy shopping lists

Let me put together a travel-friendly meal plan that won't stress you out! What kind of trip are you taking?"""


def handle_recovery_planning(user_message: str, user_profile: Dict[str, Any]) -> str:
    """Handle recovery/sick meal planning"""
    return """Feel better soon! 💙 Let me help with some comforting, nourishing meals.

I'll focus on:
🍲 Easy-to-digest soups and broths
🥣 Comforting porridges and soft foods
💧 Hydrating options
🌿 Immune-supporting ingredients

Take care of yourself - I'll keep the meal planning simple and healing! 🌸"""


def create_welcome_message(platform: str) -> str:
    """Create a warm welcome message for new users"""
    messages = [
        "Hey there! 👋 I'm your personal nutrition assistant! I can help you with meal plans, nutrition tracking, grocery lists, and answer any nutrition questions. What would you like to start with?",
        
        "Hi! So nice to meet you! 😊 I'm here to help make healthy eating easier for you. I can create meal plans, track your nutrition, make grocery lists, or answer questions. What sounds good?",
        
        "Hello! Welcome! 🌟 Think of me as your nutrition-savvy friend who's always ready to help. Whether you need meal ideas, daily nutrition tracking, or modern nutrition strategies, I've got you covered. What can I help with first?"
    ]
    
    return random.choice(messages)


def create_help_response(platform: str) -> str:
    """Create helpful response about capabilities"""
    return """I'm here to make healthy eating easy and fun! Here's what I can help you with:

🍽️ **Meal Plans** - Custom weekly plans based on your preferences
📊 **Nutrition Tracking** - Daily stats, weekly reports, feeling checks
📋 **Grocery Lists** - Shopping lists from your meal plans  
🥗 **Recipes** - Healthy recipe suggestions
💡 **Modern Nutrition** - IF, gut health, plant-forward, anti-inflammatory
🎯 **Goal Support** - Help with weight, fitness, or health goals

**Quick Commands:**
• 'stats today' - see your daily nutrition
• 'weekly report' - comprehensive summary
• 'how can I feel better?' - personalized suggestions
• Track naturally: 'ate breakfast', '2 cups water', 'feeling tired'

Just ask me naturally! Like "make me a meal plan" or "how's my protein today?" - I'll understand! 😊

What would you like to start with?"""


def create_subscription_info(platform: str) -> str:
    """Create subscription information message"""
    return """Here's how my plans work:

🆓 **Free** - 5 meal plans per month + basic nutrition tracking
💎 **Premium ($4.99/month)** - 50 meal plans + full nutrition tracking + weekly reports
🚀 **Enterprise ($9.99/month)** - Unlimited everything + advanced analytics + priority support

You can upgrade anytime by replying "UPGRADE" and I'll send you a secure payment link!

Most people love the Premium plan - it's perfect for regular meal planning and comprehensive nutrition tracking. What do you think? 😊"""


def create_upgrade_message(subscription_status: Dict[str, Any], platform: str) -> str:
    """Create friendly upgrade message"""
    plan = subscription_status.get('plan', 'Free')
    limit = subscription_status.get('limit', 5)
    
    return f"""Hey! You've used all {limit} requests in your {plan} plan this month. 

No worries though! You can upgrade to:
💎 Premium ($4.99/month) - 50 meal plans + full nutrition tracking
🚀 Enterprise ($9.99/month) - Unlimited access + advanced features

Just reply "UPGRADE" and I'll get you set up with a secure payment link! 

Thanks for being awesome! 😊"""


def send_response(message_data: Dict[str, Any], response_message: str, platform: str) -> bool:
    """Send response message back to user"""
    try:
        user_id = message_data['user_id']
        return messaging_service.send_message(platform, user_id, response_message)
        
    except Exception as e:
        logger.error(f"Error sending response: {e}")
        return False


def create_platform_response(platform: str, success: bool) -> Dict[str, Any]:
    """Create appropriate response based on platform"""
    if platform in ['whatsapp', 'sms']:
        # Twilio expects TwiML response for some endpoints
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/xml'},
            'body': '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        }
    else:
        # Other platforms expect JSON
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'success' if success else 'error'})
        }


def create_error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Create error response"""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }


def reconstruct_url(event: Dict[str, Any]) -> str:
    """Reconstruct full URL from Lambda event"""
    headers = event.get('headers', {})
    host = headers.get('Host', headers.get('host', ''))
    path = event.get('path', '')
    
    return f"https://{host}{path}"
