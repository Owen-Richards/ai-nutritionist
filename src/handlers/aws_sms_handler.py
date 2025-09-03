"""
AWS SMS Handler for Lambda Functions
Processes inbound SMS messages and sends responses using AWS End User Messaging
"""

import json
import logging
import os
from typing import Dict, Any, Optional

import boto3
from services.aws_sms_service import get_sms_service
from services.ai_service import AIService
from services.user_service import UserService
from services.meal_plan_service import MealPlanService
from handlers.spam_protection_handler import SpamProtectionService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Initialize services
sms_service = get_sms_service()
ai_service = AIService()
user_service = UserService(dynamodb)
meal_plan_service = MealPlanService(dynamodb, ai_service)
spam_service = SpamProtectionService()


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for processing AWS SMS messages
    
    Args:
        event: Lambda event (SQS records from inbound SMS)
        context: Lambda context
        
    Returns:
        Processing results
    """
    try:
        logger.info(f"Processing {len(event.get('Records', []))} SMS records")
        
        results = []
        for record in event.get('Records', []):
            result = process_sms_record(record)
            results.append(result)
        
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(f"Processed {success_count}/{len(results)} SMS messages successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'successful': success_count,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in SMS handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def process_sms_record(sqs_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single SQS record containing an inbound SMS
    
    Args:
        sqs_record: SQS record from AWS
        
    Returns:
        Processing result
    """
    try:
        # Parse the inbound SMS message
        parsed_message = sms_service.process_inbound_message(sqs_record)
        if not parsed_message:
            return {'success': False, 'error': 'Failed to parse SMS message'}
        
        user_phone = parsed_message['user_id']
        message_text = parsed_message['message'].strip()
        country_code = parsed_message.get('country_code')
        
        logger.info(f"Processing SMS from {user_phone}: {message_text[:50]}...")
        
        # 🛡️ SPAM PROTECTION AND RATE LIMITING
        protection_result = spam_service.check_message_allowed(user_phone, message_text, country_code)
        
        if not protection_result['allowed']:
            reason = protection_result['reason']
            logger.warning(f"Message rejected from {user_phone}: {reason}")
            
            # Send appropriate response based on rejection reason
            if reason == 'hourly_rate_limit_exceeded':
                response_msg = "⏰ You've reached the hourly message limit. Please try again in an hour."
            elif reason == 'daily_rate_limit_exceeded':
                response_msg = "📝 You've reached the daily message limit. Please try again tomorrow."
            elif reason == 'spam_detected':
                response_msg = "🚫 Your message was flagged as spam. Please contact support if this is an error."
            elif reason == 'number_blocked':
                # Don't respond to blocked numbers
                return {
                    'success': False,
                    'reason': 'number_blocked',
                    'action': 'no_response'
                }
            else:
                response_msg = "❌ Your message couldn't be processed. Please try again later."
            
            # Send rate limit response (if not blocked)
            if reason != 'number_blocked':
                send_response(user_phone, response_msg, country_code)
            
            return {
                'success': False,
                'reason': reason,
                'action': protection_result['action'],
                'metadata': protection_result.get('metadata', {})
            }
        
        # Handle suspicious but allowed messages
        if protection_result['action'] == 'flag_and_process':
            logger.info(f"Processing flagged message from {user_phone} (spam score: {protection_result['metadata'].get('spam_score', 0)})")
        
        # Handle opt-out requests
        if message_text.upper() in ['STOP', 'UNSUBSCRIBE', 'QUIT', 'CANCEL']:
            return handle_opt_out(user_phone, country_code)
        
        # Handle opt-in requests  
        if message_text.upper() in ['START', 'YES', 'UNSTOP', 'SUBSCRIBE']:
            return handle_opt_in(user_phone, country_code)
        
        # Get or create user
        user = user_service.get_user_by_phone(user_phone)
        if not user:
            user = user_service.create_user(user_phone, 'sms', country_code)
            # Send welcome message for new users
            welcome_response = generate_welcome_message(country_code)
            send_response(user_phone, welcome_response, country_code)
        
        # Process the message and generate response
        response_message = process_nutrition_message(user, message_text, country_code)
        
        # Send response
        send_result = send_response(user_phone, response_message, country_code)
        
        return {
            'success': True,
            'user_id': user['user_id'],
            'message_processed': message_text[:100],
            'response_sent': send_result['success'],
            'message_id': send_result.get('message_id'),
            'spam_score': protection_result.get('metadata', {}).get('spam_score', 0),
            'protection_action': protection_result['action']
        }
        
    except Exception as e:
        logger.error(f"Error processing SMS record: {str(e)}")
        return {'success': False, 'error': str(e)}


def process_nutrition_message(user: Dict[str, Any], message: str, country_code: str = None) -> str:
    """
    Process nutrition-related message and generate AI response
    
    Args:
        user: User data
        message: User's message
        country_code: User's country code
        
    Returns:
        AI-generated response message
    """
    try:
        user_id = user['user_id']
        
        # Get user preferences and dietary restrictions
        preferences = user.get('preferences', {})
        dietary_restrictions = user.get('dietary_restrictions', [])
        
        # Get country-specific configuration
        config = sms_service.get_country_config(country_code) if country_code else {}
        currency = config.get('currency', 'USD')
        measurement = config.get('measurement', 'imperial')
        
        # Detect intent and extract information
        intent = detect_message_intent(message)
        
        if intent == 'meal_plan_request':
            # Generate meal plan
            meal_plan_request = {
                'user_id': user_id,
                'dietary_restrictions': dietary_restrictions,
                'budget': extract_budget(message, currency),
                'servings': extract_servings(message),
                'preferences': preferences,
                'country_code': country_code,
                'currency': currency,
                'measurement': measurement
            }
            
            meal_plan = meal_plan_service.generate_meal_plan(meal_plan_request)
            response = format_meal_plan_response(meal_plan, measurement, currency)
            
        elif intent == 'nutrition_question':
            # Answer nutrition question
            response = ai_service.answer_nutrition_question(
                question=message,
                user_preferences=preferences,
                dietary_restrictions=dietary_restrictions,
                country_code=country_code
            )
            
        elif intent == 'recipe_request':
            # Provide recipe
            recipe_name = extract_recipe_name(message)
            response = ai_service.get_recipe_with_nutrition(
                recipe_name=recipe_name,
                dietary_restrictions=dietary_restrictions,
                measurement_system=measurement
            )
            
        elif intent == 'set_preferences':
            # Update user preferences
            new_preferences = extract_preferences(message)
            user_service.update_user_preferences(user_id, new_preferences)
            response = f"✅ Updated your preferences! {format_preferences(new_preferences)}"
            
        else:
            # General nutrition assistance
            response = ai_service.get_nutrition_advice(
                message=message,
                user_context=user,
                country_code=country_code
            )
        
        # Log the interaction
        user_service.log_interaction(user_id, message, response, 'aws_sms')
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing nutrition message: {str(e)}")
        return """I apologize, but I'm having trouble processing your request right now. 
Please try again in a few moments, or text 'help' for assistance. 🤖"""


def handle_opt_out(phone_number: str, country_code: str = None) -> Dict[str, Any]:
    """Handle SMS opt-out request"""
    try:
        # Add to AWS opt-out list
        opt_out_success = sms_service.handle_opt_out(phone_number)
        
        if opt_out_success:
            # Update user status in database
            user = user_service.get_user_by_phone(phone_number)
            if user:
                user_service.update_user_status(user['user_id'], 'opted_out')
            
            # Send confirmation (this will be the last message)
            config = sms_service.get_country_config(country_code) if country_code else {}
            language = config.get('language', 'en')
            
            if language == 'es':
                confirmation = "Has sido dado de baja. No recibirás más mensajes. Envía START para reactivar."
            elif language == 'fr':
                confirmation = "Vous êtes désabonné. Vous ne recevrez plus de messages. Envoyez START pour vous réabonner."
            else:
                confirmation = "You've been unsubscribed. You won't receive any more messages. Text START to resubscribe."
            
            sms_service.send_message(phone_number, confirmation, country_code)
            
            return {'success': True, 'action': 'opted_out'}
        else:
            return {'success': False, 'error': 'Failed to process opt-out'}
            
    except Exception as e:
        logger.error(f"Error handling opt-out: {str(e)}")
        return {'success': False, 'error': str(e)}


def handle_opt_in(phone_number: str, country_code: str = None) -> Dict[str, Any]:
    """Handle SMS opt-in request"""
    try:
        # Update user status
        user = user_service.get_user_by_phone(phone_number)
        if user:
            user_service.update_user_status(user['user_id'], 'active')
        else:
            user = user_service.create_user(phone_number, 'sms', country_code)
        
        # Send welcome message
        welcome_message = generate_welcome_message(country_code)
        result = sms_service.send_message(phone_number, welcome_message, country_code)
        
        return {'success': result['success'], 'action': 'opted_in'}
        
    except Exception as e:
        logger.error(f"Error handling opt-in: {str(e)}")
        return {'success': False, 'error': str(e)}


def send_response(phone_number: str, message: str, country_code: str = None) -> Dict[str, Any]:
    """Send SMS response to user"""
    try:
        # Truncate message if too long (SMS limit is 1600 characters)
        if len(message) > 1500:
            message = message[:1500] + "... (continued via link)"
        
        return sms_service.send_message(phone_number, message, country_code)
        
    except Exception as e:
        logger.error(f"Error sending SMS response: {str(e)}")
        return {'success': False, 'error': str(e)}


def generate_welcome_message(country_code: str = None) -> str:
    """Generate welcome message for new users"""
    config = sms_service.get_country_config(country_code) if country_code else {}
    language = config.get('language', 'en')
    currency = config.get('currency', 'USD')
    
    if language == 'es':
        return f"""¡Bienvenido al Asistente de Nutrición AI! 🥗
        
Puedo ayudarte con:
• Planes de comidas personalizados
• Consejos nutricionales  
• Recetas saludables
• Seguimiento de presupuesto ({currency})

Envía tu solicitud o pregunta sobre nutrición para empezar!"""
    elif language == 'fr':
        return f"""Bienvenue à l'Assistant Nutrition AI! 🥗
        
Je peux vous aider avec:
• Plans de repas personnalisés
• Conseils nutritionnels
• Recettes saines
• Suivi de budget ({currency})

Envoyez votre demande ou question sur la nutrition pour commencer!"""
    else:
        return f"""Welcome to AI Nutrition Assistant! 🥗
        
I can help you with:
• Personalized meal plans
• Nutrition advice
• Healthy recipes  
• Budget tracking ({currency})

Send me your nutrition request or question to get started!"""


# Helper functions for message processing
def detect_message_intent(message: str) -> str:
    """Detect the intent of the user's message"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['meal plan', 'menu', 'weekly plan', 'meal prep']):
        return 'meal_plan_request'
    elif any(word in message_lower for word in ['recipe', 'how to make', 'ingredients', 'cooking']):
        return 'recipe_request'
    elif any(word in message_lower for word in ['prefer', 'diet', 'allergic', 'restriction', 'settings']):
        return 'set_preferences'
    elif '?' in message or any(word in message_lower for word in ['what', 'how', 'why', 'when', 'should']):
        return 'nutrition_question'
    else:
        return 'general_request'


def extract_budget(message: str, currency: str) -> Optional[float]:
    """Extract budget amount from message"""
    import re
    
    # Look for currency symbols and amounts
    currency_symbols = {
        'USD': r'[\$]',
        'EUR': r'[€]', 
        'GBP': r'[£]',
        'JPY': r'[¥]',
        'INR': r'[₹]'
    }
    
    symbol = currency_symbols.get(currency, r'[\$]')
    pattern = f"{symbol}(\d+(?:\.\d{{2}})?)"
    
    match = re.search(pattern, message)
    if match:
        return float(match.group(1))
    
    # Look for numbers followed by currency code
    pattern = r'(\d+(?:\.\d{2})?)\s*' + currency
    match = re.search(pattern, message, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    return None


def extract_servings(message: str) -> int:
    """Extract number of servings from message"""
    import re
    
    # Look for patterns like "for 2 people", "4 servings", etc.
    patterns = [
        r'for (\d+) people',
        r'(\d+) people',
        r'(\d+) servings',
        r'family of (\d+)',
        r'(\d+) person'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            return int(match.group(1))
    
    return 2  # Default to 2 servings


def extract_recipe_name(message: str) -> str:
    """Extract recipe name from message"""
    # Simple extraction - look for words after "recipe for" or "how to make"
    message_lower = message.lower()
    
    if 'recipe for' in message_lower:
        return message_lower.split('recipe for')[1].strip()
    elif 'how to make' in message_lower:
        return message_lower.split('how to make')[1].strip()
    else:
        return message.strip()


def extract_preferences(message: str) -> Dict[str, Any]:
    """Extract dietary preferences from message"""
    preferences = {}
    message_lower = message.lower()
    
    # Dietary restrictions
    restrictions = []
    if 'vegetarian' in message_lower:
        restrictions.append('vegetarian')
    if 'vegan' in message_lower:
        restrictions.append('vegan')
    if 'gluten free' in message_lower or 'gluten-free' in message_lower:
        restrictions.append('gluten_free')
    if 'dairy free' in message_lower or 'lactose' in message_lower:
        restrictions.append('dairy_free')
    if 'keto' in message_lower or 'ketogenic' in message_lower:
        restrictions.append('keto')
    if 'paleo' in message_lower:
        restrictions.append('paleo')
    
    if restrictions:
        preferences['dietary_restrictions'] = restrictions
    
    return preferences


def format_preferences(preferences: Dict[str, Any]) -> str:
    """Format preferences for display"""
    if 'dietary_restrictions' in preferences:
        restrictions = ', '.join(preferences['dietary_restrictions'])
        return f"Dietary restrictions: {restrictions}"
    return "Preferences updated"


def format_meal_plan_response(meal_plan: Dict[str, Any], measurement: str, currency: str) -> str:
    """Format meal plan for SMS response"""
    if not meal_plan or 'error' in meal_plan:
        return "I couldn't generate a meal plan right now. Please try again with specific requirements (e.g., 'vegetarian meal plan for 2 people, $50 budget')."
    
    response = f"🍽️ **Your {meal_plan.get('duration', '7-day')} Meal Plan**\n"
    
    if 'budget' in meal_plan:
        response += f"💰 Budget: {currency}{meal_plan['budget']:.2f}\n"
    
    if 'meals' in meal_plan:
        for day, meals in meal_plan['meals'].items():
            response += f"\n**{day}:**\n"
            for meal_type, meal in meals.items():
                response += f"• {meal_type}: {meal['name']}\n"
    
    if 'shopping_list' in meal_plan:
        response += "\n📝 **Shopping List:** (link sent separately)"
    
    return response
