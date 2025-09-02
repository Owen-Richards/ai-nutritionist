"""
AI Nutritionist Assistant - Message Handler
Handles incoming WhatsApp/SMS messages from Twilio webhooks
"""

import json
import logging
import os
import hashlib
import hmac
import base64
from typing import Dict, Any, Optional
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError

# Import our services
from services.ai_service import AIService
from services.user_service import UserService
from services.meal_plan_service import MealPlanService
from services.twilio_service import TwilioService
from services.subscription_service import get_subscription_service

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

# Initialize services
user_service = UserService(dynamodb)
ai_service = AIService()
meal_plan_service = MealPlanService(dynamodb, ai_service)
twilio_service = TwilioService()
subscription_service = get_subscription_service()


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for processing Twilio webhook messages
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract request body and headers
        body = event.get('body', '')
        headers = event.get('headers', {})
        
        # Validate Twilio webhook signature for security
        if not validate_twilio_signature(body, headers):
            logger.warning("Invalid Twilio signature")
            return {
                'statusCode': 403,
                'body': 'Forbidden: Invalid signature'
            }
        
        # Parse Twilio webhook payload
        message_data = parse_twilio_webhook(body)
        if not message_data:
            logger.error("Failed to parse Twilio webhook")
            return {
                'statusCode': 400,
                'body': 'Bad Request: Invalid webhook format'
            }
        
        # Process the incoming message
        response_message = process_message(message_data)
        
        # Return TwiML response
        twiml_response = create_twiml_response(response_message)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/xml'
            },
            'body': twiml_response
        }
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        
        # Return generic error response
        error_twiml = create_twiml_response(
            "Sorry, I'm having technical difficulties right now. Please try again in a few minutes."
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/xml'
            },
            'body': error_twiml
        }


def validate_twilio_signature(body: str, headers: Dict[str, str]) -> bool:
    """
    Validate Twilio webhook signature for security
    """
    try:
        # Get Twilio auth token from parameter store
        auth_token = get_parameter('/ai-nutritionist/twilio/auth-token', encrypted=True)
        if not auth_token:
            logger.error("Failed to get Twilio auth token")
            return False
        
        # Get signature from headers
        signature = headers.get('X-Twilio-Signature', '')
        if not signature:
            logger.warning("No Twilio signature in headers")
            return False
        
        # Get the full URL (this would need to be constructed in a real implementation)
        url = f"https://{headers.get('Host', '')}{headers.get('X-Forwarded-Proto', 'https')}"
        
        # Create expected signature
        expected_signature = base64.b64encode(
            hmac.new(
                auth_token.encode('utf-8'),
                (url + body).encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error validating signature: {str(e)}")
        return False


def parse_twilio_webhook(body: str) -> Optional[Dict[str, str]]:
    """
    Parse Twilio webhook form data
    """
    try:
        # Parse URL-encoded form data
        from urllib.parse import parse_qs
        
        parsed_data = parse_qs(body)
        
        # Extract relevant fields
        message_data = {
            'from': parsed_data.get('From', [''])[0],
            'to': parsed_data.get('To', [''])[0],
            'body': parsed_data.get('Body', [''])[0],
            'message_sid': parsed_data.get('MessageSid', [''])[0],
            'account_sid': parsed_data.get('AccountSid', [''])[0]
        }
        
        return message_data
        
    except Exception as e:
        logger.error(f"Error parsing webhook: {str(e)}")
        return None


def process_message(message_data: Dict[str, str]) -> str:
    """
    Process incoming message and generate appropriate response
    """
    user_phone = message_data['from']
    message_text = message_data['body'].strip()
    
    logger.info(f"Processing message from {user_phone}: {message_text}")
    
    # Get or create user profile
    user_profile = user_service.get_or_create_user(user_phone)
    
    # Handle different types of messages
    if message_text.lower() in ['start', 'hello', 'hi', 'help']:
        return handle_welcome_message(user_profile)
    
    elif message_text.lower() in ['delete', 'remove', 'stop']:
        return handle_delete_user(user_profile)
    
    elif message_text.lower() in ['pricing', 'price', 'cost', 'plans']:
        return subscription_service.get_pricing_info()
    
    elif message_text.lower() in ['upgrade', 'premium', 'subscribe']:
        return handle_upgrade_request(user_profile)
    
    elif 'meal plan' in message_text.lower() or 'plan' in message_text.lower():
        return handle_meal_plan_request(user_profile, message_text)
    
    elif 'grocery' in message_text.lower() or 'shopping' in message_text.lower():
        return handle_grocery_list_request(user_profile)
    
    elif any(word in message_text.lower() for word in ['calories', 'diet', 'vegan', 'vegetarian', 'keto', 'paleo']):
        return handle_dietary_preferences(user_profile, message_text)
    
    else:
        # General AI chat for nutrition questions
        return handle_general_question(user_profile, message_text)


def handle_welcome_message(user_profile: Dict[str, Any]) -> str:
    """
    Handle welcome/start messages
    """
    if user_profile.get('is_new_user', True):
        return (
            "🥗 Welcome to AI Nutritionist! I'm here to help you plan healthy, budget-friendly meals.\n\n"
            "To get started, tell me:\n"
            "• Any dietary restrictions? (vegetarian, vegan, gluten-free, etc.)\n"
            "• Household size?\n"
            "• Weekly food budget?\n"
            "• Fitness goals? (weight loss, muscle gain, maintenance)\n\n"
            "Or just say 'meal plan' and I'll create one with default healthy options!"
        )
    else:
        return (
            f"Welcome back! 👋\n\n"
            "Ready to plan some delicious meals? Just say:\n"
            "• 'meal plan' for a new weekly plan\n"
            "• 'grocery list' for shopping list\n"
            "• Ask any nutrition questions\n\n"
            "Type 'help' for more options."
        )


def handle_upgrade_request(user_profile: Dict[str, Any]) -> str:
    """
    Handle subscription upgrade requests
    """
    user_phone = user_profile['user_id']
    subscription_status = subscription_service.get_subscription_status(user_phone)
    
    if subscription_status['tier'] != 'free':
        return f"You're already on our {subscription_status['tier'].title()} plan! 🎉\n\nEnjoy unlimited meal plans and premium features!"
    
    return """
🚀 **Ready to Upgrade?**

Choose your plan:

💎 **Premium - $4.99/month**
• Unlimited meal plans
• Custom dietary restrictions  
• Smart grocery lists
• Family meal planning
• Nutrition chat support

🏢 **Enterprise - $9.99/month**
• Everything in Premium
• Google Calendar sync
• Multi-user accounts
• Advanced analytics
• Priority support

**Payment Options:**
📱 Text "PREMIUM" for Premium plan
📱 Text "ENTERPRISE" for Enterprise plan
💳 Or visit: https://ai-nutritionist.com/subscribe

💚 **Social Impact**: Your subscription helps fund free plans for families in need and supports local farmers!

Questions? Just ask! 😊
    """.strip()


def handle_delete_user(user_profile: Dict[str, Any]) -> str:
    """
    Handle user deletion requests
    """
    try:
        user_service.delete_user(user_profile['user_id'])
        return (
            "✅ Your data has been deleted from our system.\n\n"
            "Thanks for using AI Nutritionist! Feel free to start fresh anytime by saying 'hello'."
        )
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return "Sorry, I couldn't delete your data right now. Please try again later."


def handle_meal_plan_request(user_profile: Dict[str, Any], message_text: str) -> str:
    """
    Handle meal plan generation requests
    """
    try:
        user_phone = user_profile['user_id']
        
        # Check subscription and usage limits
        usage_check = subscription_service.check_usage_limit(user_phone)
        
        if not usage_check['can_generate']:
            if usage_check['reason'] == 'usage_limit':
                # User hit free tier limit
                return subscription_service.get_upgrade_message(user_phone)
            else:
                return "Sorry, there was an issue checking your subscription. Please try again."
        
        # Update user preferences from message if provided
        user_service.update_preferences_from_message(user_profile['user_id'], message_text)
        
        # Generate meal plan
        meal_plan = meal_plan_service.generate_meal_plan(user_profile)
        
        if meal_plan:
            # Track usage for billing/limits
            subscription_service.increment_usage(user_phone)
            
            # Add subscription info to response for free users
            response = format_meal_plan_response(meal_plan)
            
            subscription_status = subscription_service.get_subscription_status(user_phone)
            if subscription_status['tier'] == 'free':
                plans_remaining = usage_check.get('plans_remaining', 0) - 1
                if plans_remaining > 0:
                    response += f"\n\n💡 You have {plans_remaining} free meal plans remaining this month. Reply 'PRICING' to see premium options!"
                else:
                    response += "\n\n🎯 This was your last free meal plan! Reply 'UPGRADE' to get unlimited plans + premium features!"
            
            return response
        else:
            return "Sorry, I couldn't generate a meal plan right now. Please try again in a few minutes."
            
    except Exception as e:
        logger.error(f"Error generating meal plan: {str(e)}")
        return "I'm having trouble creating your meal plan. Please try again shortly."


def handle_grocery_list_request(user_profile: Dict[str, Any]) -> str:
    """
    Handle grocery list requests
    """
    try:
        grocery_list = meal_plan_service.get_grocery_list(user_profile['user_id'])
        
        if grocery_list:
            return format_grocery_list_response(grocery_list)
        else:
            return "I don't have a recent meal plan to create a grocery list. Please request a meal plan first!"
            
    except Exception as e:
        logger.error(f"Error getting grocery list: {str(e)}")
        return "Sorry, I couldn't generate your grocery list right now."


def handle_dietary_preferences(user_profile: Dict[str, Any], message_text: str) -> str:
    """
    Handle dietary preference updates
    """
    try:
        user_service.update_preferences_from_message(user_profile['user_id'], message_text)
        return (
            "✅ Got it! I've updated your dietary preferences.\n\n"
            "Want me to create a new meal plan with these preferences? Just say 'meal plan'!"
        )
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return "I noted your preferences! You can ask for a meal plan anytime."


def handle_general_question(user_profile: Dict[str, Any], message_text: str) -> str:
    """
    Handle general nutrition questions using AI
    """
    try:
        # Use AI service for general nutrition advice
        response = ai_service.get_nutrition_advice(message_text, user_profile)
        return response
        
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        return (
            "I'd be happy to help with nutrition questions! Try asking about:\n"
            "• Healthy recipes\n"
            "• Meal planning tips\n"
            "• Nutrition facts\n"
            "• Dietary advice\n\n"
            "Or say 'meal plan' for a personalized weekly plan!"
        )


def format_meal_plan_response(meal_plan: Dict[str, Any]) -> str:
    """
    Format meal plan for WhatsApp/SMS display
    """
    response = "🍽️ **Your Weekly Meal Plan**\n\n"
    
    days = meal_plan.get('days', [])
    for i, day in enumerate(days, 1):
        day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i-1]
        response += f"**{day_name}:**\n"
        
        if 'breakfast' in day:
            response += f"🥐 Breakfast: {day['breakfast']}\n"
        if 'lunch' in day:
            response += f"🥙 Lunch: {day['lunch']}\n"
        if 'dinner' in day:
            response += f"🍽️ Dinner: {day['dinner']}\n"
        
        response += "\n"
    
    # Add estimated cost if available
    if 'estimated_cost' in meal_plan:
        response += f"💰 Estimated weekly cost: ${meal_plan['estimated_cost']}\n\n"
    
    response += "Say 'grocery list' for shopping list! 🛒"
    
    return response


def format_grocery_list_response(grocery_list: list) -> str:
    """
    Format grocery list for messaging
    """
    response = "🛒 **Your Grocery List**\n\n"
    
    # Group by category if available
    categories = {}
    for item in grocery_list:
        category = item.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(item['name'])
    
    for category, items in categories.items():
        response += f"**{category}:**\n"
        for item in items:
            response += f"• {item}\n"
        response += "\n"
    
    response += "Happy shopping! 🛍️"
    
    return response


def create_twiml_response(message: str) -> str:
    """
    Create TwiML response for Twilio
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>'''


def get_parameter(parameter_name: str, encrypted: bool = False) -> Optional[str]:
    """
    Get parameter from AWS Systems Manager Parameter Store
    """
    try:
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=encrypted
        )
        return response['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Error getting parameter {parameter_name}: {str(e)}")
        return None
