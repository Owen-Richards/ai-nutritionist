"""
AI Nutritionist - Universal Webhook Handler
Handles incoming messages from WhatsApp, SMS, and other platforms
Consolidated from multiple handler files for better maintainability
"""

import json
import logging
import os
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

# Import consolidated services  
from ..config.settings import get_settings
from ..config.constants import ERROR_MESSAGES, SUCCESS_MESSAGES
from ..models.user import UserProfile
from ..services.messaging.sms import SMSCommunicationService
from ..services.personalization.preferences import UserPreferencesService
from ..services.nutrition.insights import NutritionInsights
from ..services.meal_planning.planner import MealPlanningService
from ..services.business.subscription import SubscriptionService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration
settings = get_settings()

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=settings.aws.region)

# Initialize new domain services with correct class names
sms_communication_service = SMSCommunicationService()
user_preferences_service = UserPreferencesService(dynamodb)
nutrition_insights_service = NutritionInsights()
meal_planning_service = MealPlanningService(dynamodb, nutrition_insights_service)
subscription_service = SubscriptionService()

# Compatibility aliases for existing code
messaging_service = sms_communication_service
user_service = user_preferences_service
consolidated_ai_service = nutrition_insights_service
ai_service = nutrition_insights_service


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Universal Lambda handler for processing messages from any platform
    
    Args:
        event: AWS Lambda event containing webhook data
        context: AWS Lambda context object
        
    Returns:
        HTTP response for the webhook
    """
    try:
        logger.info(f"Received webhook event: {json.dumps(event, default=str)}")
        
        # Validate environment configuration
        if not settings.validate_required_settings()['valid']:
            logger.error("Invalid configuration detected")
            return _create_error_response("Service configuration error", 500)
        
        # Detect platform from event structure
        platform = messaging_service.detect_platform(event)
        if not platform:
            logger.warning("Could not detect platform from event")
            return _create_error_response("Unsupported platform")
        
        logger.info(f"Detected platform: {platform}")
        
        # Validate webhook signature for security
        if platform in ['whatsapp', 'sms']:
            if not _verify_webhook_signature(event, platform):
                logger.error("Webhook signature validation failed")
                return _create_error_response("Unauthorized", 403)
        
        # Extract message data
        message_data = messaging_service.extract_message_data(event, platform)
        if not message_data:
            logger.error("Could not extract message data from webhook")
            return _create_error_response("Invalid webhook format")
        
        # Process the message and generate response
        response_message = _process_message(message_data, platform)
        
        # Send response back to user
        success = messaging_service.send_message(
            to=message_data['phone_number'],
            message=response_message,
            platform=platform
        )
        
        if not success:
            logger.error("Failed to send response message")
        
        # Return appropriate response for platform
        return _create_platform_response(platform, success)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return _create_error_response("Internal server error", 500)


def _process_message(message_data: Dict[str, Any], platform: str) -> str:
    """
    Process incoming message and generate appropriate response
    
    Args:
        message_data: Extracted message information
        platform: Messaging platform (whatsapp, sms, etc.)
        
    Returns:
        Response message to send back to user
    """
    try:
        user_id = message_data['user_id']
        user_message = message_data['message']
        phone_number = message_data.get('phone_number')
        
        logger.info(f"Processing message from {user_id}: {user_message[:100]}...")
        
        # Get or create user profile
        user_profile = user_service.get_user_profile(user_id)
        if not user_profile:
            user_profile = _create_new_user(user_id, phone_number, platform)
            return _generate_welcome_message(user_profile, platform)
        
        # Update last interaction
        user_service.update_last_interaction(user_id)
        
        # Check subscription limits before processing
        subscription_status = subscription_service.check_user_limits(user_id)
        if subscription_status['over_limit']:
            return _create_upgrade_message(subscription_status, platform)
        
        # Classify user intent
        intent = _classify_user_intent(user_message, user_profile)
        
        # Route to appropriate handler based on intent
        response = _route_message_by_intent(intent, user_message, user_profile, platform)
        
        # Track usage for subscription management
        subscription_service.track_usage(user_id, 'message_processed')
        
        # Learn from conversation for better future responses
        _update_user_learning(user_id, user_message, response)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _create_new_user(user_id: str, phone_number: str, platform: str) -> UserProfile:
    """Create new user profile with default settings"""
    try:
        user_data = {
            'user_id': user_id,
            'phone_number': phone_number,
            'platform': platform,
            'created_at': datetime.utcnow().isoformat(),
        }
        
        user_profile = user_service.create_user_profile(user_data)
        logger.info(f"Created new user profile: {user_id}")
        return user_profile
        
    except Exception as e:
        logger.error(f"Error creating user profile: {str(e)}")
        raise


def _classify_user_intent(message: str, user_profile: UserProfile) -> str:
    """
    Classify user message intent using keyword matching and AI
    
    Returns:
        Intent category: 'meal_plan', 'nutrition', 'grocery', 'support', etc.
    """
    message_lower = message.lower()
    
    # Quick keyword-based classification first
    if any(word in message_lower for word in ['meal plan', 'meals', 'weekly plan', 'menu']):
        return 'meal_plan'
    elif any(word in message_lower for word in ['grocery', 'shopping', 'list', 'ingredients']):
        return 'grocery_list'
    elif any(word in message_lower for word in ['nutrition', 'calories', 'protein', 'carbs', 'macros']):
        return 'nutrition_tracking'
    elif any(word in message_lower for word in ['goal', 'weight loss', 'muscle gain', 'diet']):
        return 'goal_setting'
    elif any(word in message_lower for word in ['help', 'support', 'problem', 'issue']):
        return 'support'
    elif any(word in message_lower for word in ['subscribe', 'upgrade', 'premium', 'billing']):
        return 'subscription'
    elif not user_profile.onboarding_completed:
        return 'onboarding'
    else:
        return 'general_chat'


def _route_message_by_intent(intent: str, message: str, user_profile: UserProfile, platform: str) -> str:
    """Route message to appropriate service based on classified intent"""
    
    try:
        if intent == 'meal_plan':
            return _handle_meal_plan_request(message, user_profile)
        elif intent == 'grocery_list':
            return _handle_grocery_list_request(message, user_profile)
        elif intent == 'nutrition_tracking':
            return _handle_nutrition_request(message, user_profile)
        elif intent == 'goal_setting':
            return _handle_goal_setting(message, user_profile)
        elif intent == 'onboarding':
            return _handle_onboarding(message, user_profile)
        elif intent == 'subscription':
            return _handle_subscription_request(message, user_profile)
        elif intent == 'support':
            return _handle_support_request(message, user_profile)
        else:
            return _handle_general_chat(message, user_profile)
            
    except Exception as e:
        logger.error(f"Error routing message for intent {intent}: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _handle_meal_plan_request(message: str, user_profile: UserProfile) -> str:
    """Handle meal plan generation requests"""
    try:
        # Check if user has meal plan quota
        if not subscription_service.can_generate_meal_plan(user_profile.user_id):
            return _create_upgrade_message({'feature': 'meal_plans'}, 'whatsapp')
        
        # Generate meal plan based on user preferences
        meal_plan = meal_planning_service.generate_meal_plan(user_profile)
        
        if meal_plan:
            # Track usage
            subscription_service.track_usage(user_profile.user_id, 'meal_plan_generated')
            
            # Format meal plan for messaging
            formatted_plan = meal_planning_service.format_meal_plan_message(meal_plan)
            return f"{SUCCESS_MESSAGES['meal_plan_generated']}\n\n{formatted_plan}"
        else:
            return ERROR_MESSAGES["meal_generation_failed"]
            
    except Exception as e:
        logger.error(f"Error handling meal plan request: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _handle_grocery_list_request(message: str, user_profile: UserProfile) -> str:
    """Handle grocery list generation requests"""
    try:
        # Get user's active meal plan
        active_plan = meal_planning_service.get_active_meal_plan(user_profile.user_id)
        
        if not active_plan:
            return "I don't see an active meal plan. Would you like me to create one first?"
        
        # Generate grocery list
        grocery_list = meal_planning_service.generate_grocery_list(active_plan)
        
        if grocery_list:
            formatted_list = meal_planning_service.format_grocery_list_message(grocery_list)
            return f"{SUCCESS_MESSAGES['grocery_list_created']}\n\n{formatted_list}"
        else:
            return "Had trouble creating your grocery list. Let me try again."
            
    except Exception as e:
        logger.error(f"Error handling grocery list request: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _handle_nutrition_request(message: str, user_profile: UserProfile) -> str:
    """Handle nutrition tracking and advice requests"""
    try:
        # Analyze message for nutrition data
        nutrition_data = ai_service.extract_nutrition_from_message(message)
        
        if nutrition_data:
            # Log nutrition data via user service
            user_service.log_nutrition_entry(user_profile.user_id, nutrition_data)
            
            # Generate progress insights
            insights = ai_service.generate_progress_insights(user_profile.user_id)
            return f"✅ Logged your nutrition data!\n\n{insights}"
        else:
            # Provide nutrition advice
            advice = ai_service.generate_nutrition_advice(message, user_profile)
            return advice
            
    except Exception as e:
        logger.error(f"Error handling nutrition request: {str(e)}")
        return ERROR_MESSAGES["nutrition_api_error"]


def _handle_goal_setting(message: str, user_profile: UserProfile) -> str:
    """Handle goal setting and management"""
    try:
        # Extract goal from message
        goal_data = ai_service.extract_goal_from_message(message)
        
        if goal_data:
            # Add goal to user profile
            success = user_service.add_user_goal(user_profile.user_id, goal_data)
            
            if success:
                return f"{SUCCESS_MESSAGES['goal_added']} I'll factor this into your meal plans!"
            else:
                return "Had trouble adding that goal. Could you try rephrasing it?"
        else:
            return ERROR_MESSAGES["invalid_input"]
            
    except Exception as e:
        logger.error(f"Error handling goal setting: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _handle_onboarding(message: str, user_profile: UserProfile) -> str:
    """Handle user onboarding flow"""
    try:
        # Process onboarding step
        onboarding_response = user_service.process_onboarding_step(
            user_profile.user_id, 
            message
        )
        
        if user_profile.onboarding_completed:
            return f"Welcome to AI Nutritionist! 🎉\n\n{onboarding_response}"
        else:
            return onboarding_response
            
    except Exception as e:
        logger.error(f"Error handling onboarding: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _handle_subscription_request(message: str, user_profile: UserProfile) -> str:
    """Handle subscription and billing requests"""
    try:
        return subscription_service.handle_subscription_message(
            user_profile.user_id, 
            message
        )
    except Exception as e:
        logger.error(f"Error handling subscription request: {str(e)}")
        return ERROR_MESSAGES["service_unavailable"]


def _handle_support_request(message: str, user_profile: UserProfile) -> str:
    """Handle customer support requests"""
    support_response = f"""I'm here to help! 🤗

Common questions:
• "Create meal plan" - Generate weekly meals
• "Grocery list" - Get shopping list
• "Track calories" - Log your nutrition
• "Set goal" - Add nutrition goals
• "Upgrade" - View premium features

What would you like help with?"""
    
    return support_response


def _handle_general_chat(message: str, user_profile: UserProfile) -> str:
    """Handle general conversation using AI"""
    try:
        return ai_service.generate_conversational_response(message, user_profile)
    except Exception as e:
        logger.error(f"Error in general chat: {str(e)}")
        return "I'm here to help with your nutrition goals! Try asking about meal plans or nutrition tracking. 😊"


def _generate_welcome_message(user_profile: UserProfile, platform: str) -> str:
    """Generate welcome message for new users"""
    return f"""Hey there! 👋 Welcome to AI Nutritionist!

I'm your personal nutrition coach. I can help you:
• Create personalized meal plans
• Generate grocery lists
• Track your nutrition goals
• Answer food questions

Let's start! What's your main nutrition goal? (weight loss, muscle gain, healthy eating, etc.)"""


def _create_upgrade_message(limit_info: Dict[str, Any], platform: str) -> str:
    """Create subscription upgrade message"""
    feature = limit_info.get('feature', 'premium features')
    
    return f"""🔒 You've reached your monthly limit for {feature}.

Upgrade to Standard ($7/month) for:
• 20 meal plans per month
• Unlimited grocery lists  
• Custom nutrition goals
• Priority support

Reply 'upgrade' to learn more!"""


def _update_user_learning(user_id: str, message: str, response: str) -> None:
    """Update user learning based on conversation"""
    try:
        # Extract preferences and context for future use
        user_service.update_conversation_context(user_id, message, response)
    except Exception as e:
        logger.error(f"Error updating user learning: {str(e)}")


def _verify_webhook_signature(event: Dict[str, Any], platform: str) -> bool:
    """Verify webhook signature for security"""
    try:
        if platform in ['whatsapp', 'sms']:
            signature = event.get('headers', {}).get('X-Twilio-Signature', '')
            body = event.get('body', '')
            url = _reconstruct_url(event)
            
            return messaging_service.verify_twilio_signature(signature, body, url)
        
        # Add other platform verification as needed
        return True
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


def _reconstruct_url(event: Dict[str, Any]) -> str:
    """Reconstruct the original webhook URL for signature verification"""
    try:
        headers = event.get('headers', {})
        host = headers.get('Host', '')
        path = event.get('requestContext', {}).get('path', '')
        stage = event.get('requestContext', {}).get('stage', '')
        
        if stage and stage != 'prod':
            return f"https://{host}/{stage}{path}"
        else:
            return f"https://{host}{path}"
            
    except Exception as e:
        logger.error(f"Error reconstructing URL: {str(e)}")
        return ""


def _create_platform_response(platform: str, success: bool) -> Dict[str, Any]:
    """Create appropriate response format for each platform"""
    status_code = 200 if success else 500
    
    if platform in ['whatsapp', 'sms']:
        # Twilio expects TwiML response
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/xml'},
            'body': '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
        }
    else:
        # Generic JSON response
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': success})
        }


def _create_error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Create error response"""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }
