"""
Consolidated Messaging Service

Unified messaging service that handles:
- Multi-platform messaging (WhatsApp, SMS, Telegram, etc.)
- AWS End User Messaging integration
- Nutrition-specific messaging patterns
- Enhanced user experience features
- International messaging support
- Performance optimization and caching

Consolidates functionality from:
- messaging_service.py
- nutrition_messaging_service.py  
- aws_sms_service.py
- multi_user_messaging_handler.py
- enhanced_user_experience_service.py
"""

import json
import logging
import hashlib
import hmac
import boto3
import re
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from botocore.exceptions import ClientError
import requests
import os

logger = logging.getLogger(__name__)

class MessagePlatform(ABC):
    """Abstract base class for messaging platforms"""
    
    @abstractmethod
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send a message through the platform"""
        pass
    
    @abstractmethod
    def validate_webhook(self, signature: str, body: str, url: str) -> bool:
        """Validate incoming webhook signature"""
        pass
    
    @abstractmethod
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse incoming message data"""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Get platform identifier"""
        pass

class WhatsAppPlatform(MessagePlatform):
    """WhatsApp messaging via Twilio"""
    
    def __init__(self):
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.from_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send WhatsApp message via Twilio"""
        try:
            # Ensure WhatsApp format
            if not to.startswith('whatsapp:'):
                to = f'whatsapp:{to}'
            
            message_kwargs = {
                'body': message,
                'from_': self.from_number,
                'to': to
            }
            
            if media_url:
                message_kwargs['media_url'] = [media_url]
            
            message = self.client.messages.create(**message_kwargs)
            logger.info(f"WhatsApp message sent: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    def validate_webhook(self, signature: str, body: str, url: str) -> bool:
        """Validate Twilio webhook signature"""
        try:
            validator = RequestValidator(self.auth_token)
            return validator.validate(url, body, signature)
        except Exception as e:
            logger.error(f"Error validating WhatsApp webhook: {str(e)}")
            return False
    
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Twilio WhatsApp webhook data"""
        try:
            return {
                'platform': 'whatsapp',
                'user_id': webhook_data.get('From', '').replace('whatsapp:', ''),
                'message': webhook_data.get('Body', ''),
                'media_url': webhook_data.get('MediaUrl0'),
                'raw_data': webhook_data
            }
        except Exception as e:
            logger.error(f"Error parsing WhatsApp message: {str(e)}")
            return None
    
    def get_platform_name(self) -> str:
        return "whatsapp"

class SMSPlatform(MessagePlatform):
    """Regular SMS messaging via Twilio"""
    
    def __init__(self):
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.from_number = os.getenv('TWILIO_SMS_NUMBER')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send SMS message via Twilio"""
        try:
            # Clean phone number format
            if to.startswith('whatsapp:'):
                to = to.replace('whatsapp:', '')
            
            message_kwargs = {
                'body': message,
                'from_': self.from_number,
                'to': to
            }
            
            if media_url:
                message_kwargs['media_url'] = [media_url]
            
            message = self.client.messages.create(**message_kwargs)
            logger.info(f"SMS message sent: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS message: {str(e)}")
            return False
    
    def validate_webhook(self, signature: str, body: str, url: str) -> bool:
        """Validate Twilio webhook signature"""
        try:
            validator = RequestValidator(self.auth_token)
            return validator.validate(url, body, signature)
        except Exception as e:
            logger.error(f"Error validating SMS webhook: {str(e)}")
            return False
    
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Twilio SMS webhook data"""
        try:
            return {
                'platform': 'sms',
                'user_id': webhook_data.get('From', ''),
                'message': webhook_data.get('Body', ''),
                'media_url': webhook_data.get('MediaUrl0'),
                'raw_data': webhook_data
            }
        except Exception as e:
            logger.error(f"Error parsing SMS message: {str(e)}")
            return None
    
    def get_platform_name(self) -> str:
        return "sms"

class TelegramPlatform(MessagePlatform):
    """Telegram messaging via Bot API"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_secret = os.getenv('TELEGRAM_WEBHOOK_SECRET')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send Telegram message"""
        try:
            if media_url:
                # Send photo with caption
                url = f"{self.api_url}/sendPhoto"
                data = {
                    'chat_id': to,
                    'photo': media_url,
                    'caption': message,
                    'parse_mode': 'Markdown'
                }
            else:
                # Send text message
                url = f"{self.api_url}/sendMessage"
                data = {
                    'chat_id': to,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent to {to}")
                return True
            else:
                logger.error(f"Telegram API error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return False
    
    def validate_webhook(self, signature: str, body: str, url: str) -> bool:
        """Validate Telegram webhook signature"""
        try:
            if not self.webhook_secret:
                return True  # No secret configured
            
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                body.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error validating Telegram webhook: {str(e)}")
            return False
    
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Telegram webhook data"""
        try:
            message = webhook_data.get('message', {})
            
            return {
                'platform': 'telegram',
                'user_id': str(message.get('from', {}).get('id', '')),
                'message': message.get('text', ''),
                'media_url': None,  # Handle photos/media separately if needed
                'raw_data': webhook_data
            }
        except Exception as e:
            logger.error(f"Error parsing Telegram message: {str(e)}")
            return None
    
    def get_platform_name(self) -> str:
        return "telegram"

class MessengerPlatform(MessagePlatform):
    """Facebook Messenger via Graph API"""
    
    def __init__(self):
        self.access_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET')
        self.api_url = "https://graph.facebook.com/v18.0/me/messages"
    
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send Facebook Messenger message"""
        try:
            headers = {'Content-Type': 'application/json'}
            
            if media_url:
                # Send image with text
                data = {
                    'recipient': {'id': to},
                    'message': {
                        'attachment': {
                            'type': 'image',
                            'payload': {'url': media_url}
                        }
                    },
                    'access_token': self.access_token
                }
            else:
                # Send text message
                data = {
                    'recipient': {'id': to},
                    'message': {'text': message},
                    'access_token': self.access_token
                }
            
            response = requests.post(self.api_url, json=data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Messenger message sent to {to}")
                return True
            else:
                logger.error(f"Messenger API error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Messenger message: {str(e)}")
            return False
    
    def validate_webhook(self, signature: str, body: str, url: str) -> bool:
        """Validate Facebook webhook signature"""
        try:
            if not self.app_secret:
                return True
            
            expected_signature = hmac.new(
                self.app_secret.encode(),
                body.encode(),
                hashlib.sha1
            ).hexdigest()
            
            return hmac.compare_digest(f"sha1={expected_signature}", signature)
            
        except Exception as e:
            logger.error(f"Error validating Messenger webhook: {str(e)}")
            return False
    
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Facebook Messenger webhook data"""
        try:
            entry = webhook_data.get('entry', [{}])[0]
            messaging = entry.get('messaging', [{}])[0]
            
            return {
                'platform': 'messenger',
                'user_id': messaging.get('sender', {}).get('id', ''),
                'message': messaging.get('message', {}).get('text', ''),
                'media_url': None,
                'raw_data': webhook_data
            }
        except Exception as e:
            logger.error(f"Error parsing Messenger message: {str(e)}")
            return None
    
    def get_platform_name(self) -> str:
        return "messenger"

class UniversalMessagingService:
    """
    Universal messaging service that works across all platforms
    Makes the AI nutritionist feel like "just another contact"
    """
    
    def __init__(self):
        # Initialize all available platforms
        self.platforms = {}
        
        # Add platforms based on available credentials
        try:
            if os.getenv('TWILIO_ACCOUNT_SID'):
                self.platforms['whatsapp'] = WhatsAppPlatform()
                self.platforms['sms'] = SMSPlatform()
        except Exception as e:
            logger.warning(f"Could not initialize Twilio platforms: {e}")
        
        try:
            if os.getenv('TELEGRAM_BOT_TOKEN'):
                self.platforms['telegram'] = TelegramPlatform()
        except Exception as e:
            logger.warning(f"Could not initialize Telegram platform: {e}")
        
        try:
            if os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN'):
                self.platforms['messenger'] = MessengerPlatform()
        except Exception as e:
            logger.warning(f"Could not initialize Messenger platform: {e}")
        
        logger.info(f"Initialized messaging platforms: {list(self.platforms.keys())}")
    
    def send_message(self, platform: str, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send message via specified platform"""
        if platform not in self.platforms:
            logger.error(f"Platform {platform} not available")
            return False
        
        return self.platforms[platform].send_message(to, message, media_url)
    
    def send_to_all_user_platforms(self, user_id: str, message: str, media_url: Optional[str] = None) -> Dict[str, bool]:
        """Send message to user across all their registered platforms"""
        results = {}
        
        # In a real implementation, you'd lookup user's preferred platforms from DB
        # For now, try WhatsApp first (most common), then SMS fallback
        for platform_name in ['whatsapp', 'sms', 'telegram', 'messenger']:
            if platform_name in self.platforms:
                success = self.send_message(platform_name, user_id, message, media_url)
                results[platform_name] = success
                if success:
                    break  # Stop after first successful delivery
        
        return results
    
    def validate_webhook(self, platform: str, signature: str, body: str, url: str) -> bool:
        """Validate webhook for specified platform"""
        if platform not in self.platforms:
            return False
        
        return self.platforms[platform].validate_webhook(signature, body, url)
    
    def parse_incoming_message(self, platform: str, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse incoming message from specified platform"""
        if platform not in self.platforms:
            return None
        
        return self.platforms[platform].parse_incoming_message(webhook_data)
    
    def get_available_platforms(self) -> List[str]:
        """Get list of available messaging platforms"""
        return list(self.platforms.keys())
    
    def format_friendly_message(self, message: str, platform: str = 'whatsapp') -> str:
        """
        Format message to feel natural and friendly across platforms
        Like texting a knowledgeable friend about nutrition
        """
        # Add platform-specific formatting
        if platform == 'telegram':
            # Telegram supports markdown
            message = message.replace('**', '*')  # Bold formatting
        elif platform == 'whatsapp':
            # WhatsApp uses different formatting
            message = message.replace('**', '*')  # Bold formatting
        
        # Add friendly emojis and conversational tone
        friendly_starters = [
            "Hey! 👋 ",
            "Hi there! 😊 ",
            "Hello! 🌟 ",
            ""  # Sometimes no starter for variety
        ]
        
        # Add natural conversational elements
        if not any(starter in message for starter in ["Hi", "Hey", "Hello"]):
            import random
            starter = random.choice(friendly_starters)
            message = starter + message
        
        return message
    
    def create_contact_experience(self, user_message: str, user_profile: Dict[str, Any]) -> str:
        """
        Create a natural contact-like experience
        Respond like a knowledgeable friend who happens to know nutrition
        """
        # Detect message intent and respond naturally
        message_lower = user_message.lower()
        
        # Casual greetings
        if any(word in message_lower for word in ['hi', 'hey', 'hello', 'morning', 'evening']):
            responses = [
                f"Hey {user_profile.get('name', 'there')}! 😊 How's your day going? Need any nutrition help?",
                f"Hi {user_profile.get('name', 'friend')}! 👋 What's on your mind nutrition-wise today?",
                f"Hello! 🌟 Ready to tackle some nutrition goals together?"
            ]
            import random
            return random.choice(responses)
        
        return "I'm here to help with your nutrition questions! What's up? 😊"


class AWSMessagingPlatform(MessagePlatform):
    """AWS End User Messaging platform integration"""
    
    def __init__(self):
        self.sms_client = boto3.client('pinpoint-sms-voice-v2')
        self.whatsapp_client = boto3.client('pinpoint')
        self.ssm = boto3.client('ssm')
        self.sqs = boto3.client('sqs')
        
        # Configuration
        self.phone_pool_id = os.getenv('PHONE_POOL_ID')
        self.configuration_set = os.getenv('SMS_CONFIG_SET')
        self.whatsapp_application_id = os.getenv('WHATSAPP_APPLICATION_ID')
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        
        # International support
        self.COUNTRY_CONFIGS = {
            'US': {'currency': 'USD', 'language': 'en', 'measurement': 'imperial', 'timezone': 'America/New_York'},
            'UK': {'currency': 'GBP', 'language': 'en', 'measurement': 'metric', 'timezone': 'Europe/London'},
            'AU': {'currency': 'AUD', 'language': 'en', 'measurement': 'metric', 'timezone': 'Australia/Sydney'},
            'CA': {'currency': 'CAD', 'language': 'en', 'measurement': 'metric', 'timezone': 'America/Toronto'},
            'IN': {'currency': 'INR', 'language': 'en', 'measurement': 'metric', 'timezone': 'Asia/Kolkata'},
            'BR': {'currency': 'BRL', 'language': 'pt', 'measurement': 'metric', 'timezone': 'America/Sao_Paulo'},
            'DE': {'currency': 'EUR', 'language': 'de', 'measurement': 'metric', 'timezone': 'Europe/Berlin'},
            'FR': {'currency': 'EUR', 'language': 'fr', 'measurement': 'metric', 'timezone': 'Europe/Paris'},
            'JP': {'currency': 'JPY', 'language': 'ja', 'measurement': 'metric', 'timezone': 'Asia/Tokyo'},
            'SG': {'currency': 'SGD', 'language': 'en', 'measurement': 'metric', 'timezone': 'Asia/Singapore'}
        }
    
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send message via AWS End User Messaging"""
        try:
            if self._is_whatsapp_number(to):
                return self._send_whatsapp_via_aws(to, message, media_url)
            else:
                return self._send_sms_via_aws(to, message, media_url)
        except Exception as e:
            logger.error(f"Error sending AWS message: {str(e)}")
            return False
    
    def _send_sms_via_aws(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send SMS via AWS Pinpoint SMS"""
        try:
            response = self.sms_client.send_text_message(
                DestinationPhoneNumber=to,
                MessageBody=message,
                OriginationIdentity=self._get_origination_number(),
                ConfigurationSetName=self.configuration_set
            )
            logger.info(f"AWS SMS sent: {response.get('MessageId')}")
            return True
        except ClientError as e:
            logger.error(f"AWS SMS error: {str(e)}")
            return False
    
    def _send_whatsapp_via_aws(self, to: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send WhatsApp via AWS Pinpoint"""
        try:
            message_request = {
                'Addresses': {
                    to: {'ChannelType': 'VOICE'}  # Will be updated for WhatsApp
                },
                'MessageConfiguration': {
                    'SMSMessage': {
                        'Body': message,
                        'MessageType': 'TRANSACTIONAL'
                    }
                }
            }
            
            response = self.whatsapp_client.send_messages(
                ApplicationId=self.whatsapp_application_id,
                MessageRequest=message_request
            )
            logger.info(f"AWS WhatsApp sent: {response.get('MessageResponse', {}).get('RequestId')}")
            return True
        except ClientError as e:
            logger.error(f"AWS WhatsApp error: {str(e)}")
            return False
    
    def _is_whatsapp_number(self, number: str) -> bool:
        """Check if number is WhatsApp format"""
        return number.startswith('whatsapp:')
    
    def _get_origination_number(self) -> str:
        """Get origination number from SSM or environment"""
        if hasattr(self, '_cached_origination_number'):
            return self._cached_origination_number
        
        try:
            response = self.ssm.get_parameter(
                Name=f"/{self.environment}/messaging/origination-number"
            )
            self._cached_origination_number = response['Parameter']['Value']
            return self._cached_origination_number
        except:
            return os.getenv('AWS_ORIGINATION_NUMBER', '+1234567890')
    
    def validate_webhook(self, signature: str, body: str, url: str) -> bool:
        """Validate AWS webhook signature"""
        # AWS webhook validation logic
        return True  # Implement based on AWS documentation
    
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse AWS webhook data"""
        try:
            return {
                'platform': 'aws',
                'user_id': webhook_data.get('originationNumber', ''),
                'message': webhook_data.get('messageBody', ''),
                'raw_data': webhook_data
            }
        except Exception as e:
            logger.error(f"Error parsing AWS message: {str(e)}")
            return None
    
    def get_platform_name(self) -> str:
        return "aws"


class NutritionMessagingFeatures:
    """
    Nutrition-specific messaging patterns and UX enhancements
    Provides battle-tested copy for daily nudges, recaps, and feeling checks
    """
    
    def __init__(self):
        # Template snack buttons for quick tracking
        self.snack_templates = {
            'fruit': '🍎 Fruit',
            'yogurt': '🥛 Yogurt', 
            'protein_bar': '🍫 Protein Bar',
            'nuts': '🥜 Nuts',
            'custom': '✍️ Custom'
        }
        
        # Portion multiplier options
        self.portion_options = {
            '0.5': '½x',
            '1.0': '1x', 
            '1.5': '1.5x',
            '2.0': '2x'
        }
        
        # Feeling check emojis
        self.feeling_scales = {
            'mood': ['😞', '😐', '🙂', '😄'],
            'energy': ['💤', '⚡'],
            'digestion': ['😣', '🙂', '👍'],
            'sleep': ['😴', '😴😴', '😴😴😴']
        }
    
    def create_daily_nudge(self, user_profile: Dict[str, Any]) -> str:
        """Create personalized daily nutrition nudge"""
        name = user_profile.get('name', 'there')
        goal = user_profile.get('primary_goal', 'health')
        
        nudges = {
            'weight_loss': [
                f"Morning {name}! 🌅 Ready to fuel your weight loss goals today? What's for breakfast?",
                f"Hey {name}! 💪 Yesterday's progress counts - what healthy choice will you make first today?",
                f"Good morning! ☀️ Your weight loss journey continues - how are you feeling about today's nutrition?"
            ],
            'muscle_gain': [
                f"Morning {name}! 💪 Time to feed those muscles - protein planning for today?",
                f"Hey {name}! 🏋️ Your body's ready to grow - what's your first protein hit today?",
                f"Good morning! 🌟 Muscle-building day ahead - feeling prepared nutrition-wise?"
            ],
            'health': [
                f"Morning {name}! 🌿 Ready for another day of nourishing your body well?",
                f"Hey {name}! 🌱 What healthy choices feel right for you today?",
                f"Good morning! ✨ How can I help you eat well today?"
            ]
        }
        
        import random
        return random.choice(nudges.get(goal, nudges['health']))
    
    def create_feeling_check(self, time_of_day: str = 'evening') -> str:
        """Create feeling check message"""
        if time_of_day == 'evening':
            return (
                "Quick feeling check! 🌙 How are you feeling after today's nutrition choices?\n\n"
                "Energy: 💤 Low | ⚡ High\n"
                "Mood: 😞 Down | 😐 Okay | 🙂 Good | 😄 Great\n"
                "Digestion: 😣 Uncomfortable | 🙂 Fine | 👍 Great\n\n"
                "Just respond with emojis! This helps me personalize your plan."
            )
        else:
            return (
                "Morning check-in! ☀️ How did you sleep and what's your energy like?\n\n"
                "Sleep: 😴 Poor | 😴😴 Okay | 😴😴😴 Great\n"
                "Energy: 💤 Low | ⚡ High\n\n"
                "Let me know with emojis!"
            )
    
    def create_weekly_recap(self, user_stats: Dict[str, Any]) -> str:
        """Create encouraging weekly nutrition recap"""
        name = user_stats.get('name', 'there')
        days_tracked = user_stats.get('days_tracked', 0)
        goals_hit = user_stats.get('goals_hit', 0)
        total_goals = user_stats.get('total_goals', 7)
        
        if days_tracked >= 5:
            energy = "🔥"
            tone = "amazing"
        elif days_tracked >= 3:
            energy = "💪"
            tone = "solid"
        else:
            energy = "🌱"
            tone = "growing"
        
        return f"""
{energy} {name}, your week in nutrition!

📊 Days tracked: {days_tracked}/7
🎯 Goals hit: {goals_hit}/{total_goals}
📈 That's {tone} progress!

{self._get_weekly_encouragement(days_tracked, goals_hit, total_goals)}

Ready to make next week even better? What's one thing you want to focus on? 🚀
        """.strip()
    
    def _get_weekly_encouragement(self, days_tracked: int, goals_hit: int, total_goals: int) -> str:
        """Get encouraging message based on weekly performance"""
        success_rate = goals_hit / total_goals if total_goals > 0 else 0
        
        if success_rate >= 0.8:
            return "🌟 You're absolutely crushing it! Your consistency is inspiring."
        elif success_rate >= 0.6:
            return "💪 Strong week! You're building great habits that will last."
        elif success_rate >= 0.4:
            return "🌱 Good progress! Every small step is moving you forward."
        else:
            return "🤗 Every start is valuable! Tomorrow is a fresh opportunity to nourish yourself well."
    
    def format_macro_summary(self, macros: Dict[str, float], goals: Dict[str, float]) -> str:
        """Format macronutrient summary with visual progress"""
        def get_progress_bar(current: float, goal: float, length: int = 8) -> str:
            if goal == 0:
                return "━" * length
            
            filled = min(int((current / goal) * length), length)
            return "█" * filled + "━" * (length - filled)
        
        protein_bar = get_progress_bar(macros.get('protein', 0), goals.get('protein', 1))
        carbs_bar = get_progress_bar(macros.get('carbs', 0), goals.get('carbs', 1))
        fat_bar = get_progress_bar(macros.get('fat', 0), goals.get('fat', 1))
        
        return f"""
📊 Today's Macros:

🥩 Protein: {macros.get('protein', 0):.0f}g / {goals.get('protein', 0):.0f}g
{protein_bar}

🍞 Carbs: {macros.get('carbs', 0):.0f}g / {goals.get('carbs', 0):.0f}g  
{carbs_bar}

🥑 Fat: {macros.get('fat', 0):.0f}g / {goals.get('fat', 0):.0f}g
{fat_bar}

💪 Keep it up!
        """.strip()


class EnhancedUserExperience:
    """Enhanced UX features for messaging"""
    
    def __init__(self):
        self.quick_actions = {
            'log_meal': '🍽️ Log Meal',
            'get_recipe': '📝 Get Recipe',
            'check_progress': '📊 Check Progress',
            'ask_question': '❓ Ask Question',
            'plan_tomorrow': '📅 Plan Tomorrow'
        }
    
    def create_smart_suggestions(self, user_context: Dict[str, Any]) -> List[str]:
        """Create contextual smart suggestions based on user behavior"""
        suggestions = []
        time_of_day = datetime.now().hour
        last_log = user_context.get('last_meal_log')
        
        # Time-based suggestions
        if 6 <= time_of_day <= 10:
            suggestions.extend([
                "🌅 Log breakfast",
                "🥤 Morning protein shake recipe",
                "☕ Healthy coffee additions"
            ])
        elif 11 <= time_of_day <= 14:
            suggestions.extend([
                "🥗 Quick lunch ideas",
                "🍽️ Log lunch", 
                "💡 Afternoon snack prep"
            ])
        elif 17 <= time_of_day <= 21:
            suggestions.extend([
                "🍳 Dinner planning",
                "🍽️ Log dinner",
                "📊 Check today's progress"
            ])
        
        # Behavior-based suggestions
        if not last_log or (datetime.now() - datetime.fromisoformat(last_log)).hours > 4:
            suggestions.append("⏰ Haven't logged in a while - catch up?")
        
        return suggestions[:3]  # Limit to top 3
    
    def create_onboarding_flow(self, step: int) -> Dict[str, Any]:
        """Create step-by-step onboarding messages"""
        flows = {
            1: {
                'message': "Welcome! 👋 I'm your personal nutrition assistant. Let's start by learning about your goals.\n\nWhat's your main nutrition goal?",
                'options': ['🏃 Weight Loss', '💪 Muscle Gain', '🌿 General Health', '⚖️ Weight Maintenance']
            },
            2: {
                'message': "Great choice! Now, what's your experience level with nutrition tracking?",
                'options': ['🔰 Beginner', '📈 Intermediate', '🎯 Advanced', '👨‍⚕️ Professional']
            },
            3: {
                'message': "Perfect! Let's set up your preferences. How do you like to receive updates?",
                'options': ['📱 Daily check-ins', '📊 Weekly summaries', '🎯 Goal reminders only', '🤐 Minimal notifications']
            }
        }
        
        return flows.get(step, {'message': 'Setup complete! 🎉', 'options': []})


# Enhanced consolidated messaging service
class ConsolidatedMessagingService(UniversalMessagingService):
    """
    Consolidated messaging service with all features:
    - Multi-platform support (Twilio, AWS, etc.)
    - Nutrition-specific messaging patterns
    - Enhanced user experience features
    - International support
    """
    
    def __init__(self):
        super().__init__()
        
        # Add AWS platform
        self.platforms['aws'] = AWSMessagingPlatform()
        
        # Initialize feature modules
        self.nutrition_features = NutritionMessagingFeatures()
        self.user_experience = EnhancedUserExperience()
        
        # Performance optimizations
        self._message_cache = {}
        self._template_cache = {}
    
    def send_nutrition_message(self, to: str, message_type: str, user_profile: Dict[str, Any], 
                             platform: str = 'whatsapp', **kwargs) -> bool:
        """Send nutrition-specific formatted message"""
        
        # Generate message based on type
        if message_type == 'daily_nudge':
            message = self.nutrition_features.create_daily_nudge(user_profile)
        elif message_type == 'feeling_check':
            time_of_day = kwargs.get('time_of_day', 'evening')
            message = self.nutrition_features.create_feeling_check(time_of_day)
        elif message_type == 'weekly_recap':
            user_stats = kwargs.get('user_stats', {})
            message = self.nutrition_features.create_weekly_recap({**user_profile, **user_stats})
        elif message_type == 'macro_summary':
            macros = kwargs.get('macros', {})
            goals = kwargs.get('goals', {})
            message = self.nutrition_features.format_macro_summary(macros, goals)
        else:
            message = kwargs.get('message', 'Hello! How can I help with your nutrition today?')
        
        # Apply friendly formatting
        formatted_message = self.format_friendly_message(message, platform)
        
        # Send via specified platform
        return self.send_message(to, formatted_message, platform)
    
    def get_smart_suggestions(self, user_id: str, user_context: Dict[str, Any]) -> List[str]:
        """Get contextual smart suggestions for user"""
        return self.user_experience.create_smart_suggestions(user_context)
    
    def handle_onboarding(self, user_id: str, step: int) -> Dict[str, Any]:
        """Handle onboarding flow for new users"""
        return self.user_experience.create_onboarding_flow(step)
    
    def cache_message_template(self, template_id: str, template: str) -> None:
        """Cache frequently used message templates"""
        self._template_cache[template_id] = template
    
    def get_cached_template(self, template_id: str) -> Optional[str]:
        """Retrieve cached message template"""
        return self._template_cache.get(template_id)
