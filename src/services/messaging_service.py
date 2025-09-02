"""
Universal Messaging Service
Supports multiple messaging platforms: WhatsApp, SMS, Telegram, Facebook Messenger, etc.
"""

import json
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from twilio.rest import Client
from twilio.request_validator import RequestValidator
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
                f"Hi! Good to hear from you! What's on your mind nutrition-wise today?",
                f"Hello! 👋 Ready to tackle some healthy eating goals together?"
            ]
            import random
            return random.choice(responses)
        
        # Quick questions
        elif any(word in message_lower for word in ['quick', 'fast', 'simple']):
            return "Sure thing! I love quick nutrition questions. What's up? 🚀"
        
        # Meal planning requests
        elif any(word in message_lower for word in ['meal', 'plan', 'week', 'recipe']):
            return "Awesome! I'm excited to help you plan some delicious, healthy meals. Let me think about what would work best for you... 🍽️"
        
        # Default friendly response
        else:
            return "Got it! Let me help you with that. Give me just a moment to put together a great response... 💭"
