"""
Twilio Service for sending WhatsApp/SMS messages with international support
"""

import json
import logging
import os
import urllib.parse
from typing import Dict, Any, Optional, List
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for sending messages via Twilio with international support"""
    
    # International phone number configurations
    COUNTRY_CONFIGS = {
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
    
    def __init__(self):
        self.ssm = boto3.client('ssm')
        self._account_sid = None
        self._auth_token = None
        self._from_number = None
    
    def send_message(self, to_number: str, message: str, media_url: str = None, 
                     country_code: str = None) -> bool:
        """
        Send WhatsApp or SMS message via Twilio with international support
        
        Args:
            to_number: Phone number in international format (+1234567890)
            message: Message text
            media_url: Optional media URL
            country_code: Optional country code for localization
        """
        try:
            # Validate and format phone number
            formatted_number = self._format_international_number(to_number)
            if not formatted_number:
                logger.error(f"Invalid phone number format: {to_number}")
                return False
            
            # Get country configuration if provided
            config = self.get_country_config(country_code) if country_code else None
            
            # Localize message if needed
            if config and config.get('language') != 'en':
                # In production, you'd use a translation service here
                logger.info(f"Would translate message to {config['language']}")
            
            # For now, we'll return True as the actual Twilio SDK isn't installed
            # In production, this would use the Twilio REST API
            logger.info(f"Would send message to {formatted_number}: {message[:50]}...")
            
            # Placeholder for actual Twilio implementation:
            # from twilio.rest import Client
            # client = Client(self._get_account_sid(), self._get_auth_token())
            # 
            # message = client.messages.create(
            #     body=message,
            #     from_=self._get_from_number(),
            #     to=formatted_number,
            #     media_url=[media_url] if media_url else None
            # )
            # 
            # logger.info(f"Message sent successfully: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to {to_number}: {str(e)}")
            return False
    
    def send_whatsapp_message(self, to_number: str, message: str, media_url: str = None,
                             country_code: str = None) -> bool:
        """
        Send WhatsApp message specifically with international support
        """
        try:
            # Format phone number for WhatsApp
            formatted_number = self._format_international_number(to_number)
            whatsapp_to = f"whatsapp:{formatted_number}"
            whatsapp_from = f"whatsapp:{self._get_from_number()}"
            
            # Check if it's business hours in user's country
            if country_code and not self._is_business_hours(country_code):
                logger.info(f"Sending outside business hours for {country_code}")
                # You might want to queue the message or add a note
            
            logger.info(f"Would send WhatsApp message to {whatsapp_to}: {message[:50]}...")
            
            # Placeholder for actual implementation
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {to_number}: {str(e)}")
            return False
    
    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send SMS message
        """
        try:
            logger.info(f"Would send SMS to {to_number}: {message[:50]}...")
            
            # Placeholder for actual implementation
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {str(e)}")
            return False
    
    def _get_account_sid(self) -> str:
        """Get Twilio Account SID from parameter store"""
        if not self._account_sid:
            self._account_sid = self._get_parameter('/ai-nutritionist/twilio/account-sid')
        return self._account_sid
    
    def _get_auth_token(self) -> str:
        """Get Twilio Auth Token from parameter store"""
        if not self._auth_token:
            self._auth_token = self._get_parameter('/ai-nutritionist/twilio/auth-token', encrypted=True)
        return self._auth_token
    
    def _get_from_number(self) -> str:
        """Get Twilio phone number from parameter store"""
        if not self._from_number:
            self._from_number = self._get_parameter('/ai-nutritionist/twilio/phone-number')
        return self._from_number
    
    def _get_parameter(self, parameter_name: str, encrypted: bool = False) -> Optional[str]:
        """Get parameter from AWS Systems Manager Parameter Store"""
        try:
            response = self.ssm.get_parameter(
                Name=parameter_name,
                WithDecryption=encrypted
            )
            return response['Parameter']['Value']
        except ClientError as e:
            logger.error(f"Error getting parameter {parameter_name}: {str(e)}")
            return None
    
    def _format_international_number(self, phone_number: str) -> Optional[str]:
        """
        Format phone number to international E.164 format
        
        Args:
            phone_number: Phone number in various formats
            
        Returns:
            Formatted number (+1234567890) or None if invalid
        """
        try:
            # Remove all non-digit characters except +
            clean_number = ''.join(c for c in phone_number if c.isdigit() or c == '+')
            
            # Ensure it starts with +
            if not clean_number.startswith('+'):
                # If it starts with 00, replace with +
                if clean_number.startswith('00'):
                    clean_number = '+' + clean_number[2:]
                # If it's a US number without country code, add +1
                elif len(clean_number) == 10:
                    clean_number = '+1' + clean_number
                else:
                    clean_number = '+' + clean_number
            
            # Basic validation - should be 10-15 digits after +
            digits_only = clean_number[1:]
            if not (10 <= len(digits_only) <= 15):
                return None
                
            return clean_number
            
        except Exception as e:
            logger.error(f"Error formatting phone number {phone_number}: {str(e)}")
            return None
    
    def get_country_config(self, country_code: str) -> Dict[str, Any]:
        """Get localized configuration for country"""
        return self.COUNTRY_CONFIGS.get(country_code.upper(), self.COUNTRY_CONFIGS['US'])
    
    def _is_business_hours(self, country_code: str) -> bool:
        """
        Check if it's business hours in the user's country (8 AM - 10 PM)
        """
        try:
            # For now, return True - in production you'd use pytz
            # config = self.get_country_config(country_code)
            # timezone = config.get('timezone', 'UTC')
            # local_time = datetime.now(pytz.timezone(timezone))
            # return 8 <= local_time.hour <= 22
            return True
        except Exception:
            return True
    
    def generate_whatsapp_link(self, phone_number: str, message: str = None) -> str:
        """
        Generate WhatsApp link for any international number
        
        Args:
            phone_number: International phone number
            message: Optional pre-filled message
            
        Returns:
            WhatsApp link (wa.me format)
        """
        try:
            # Remove + and format for wa.me
            clean_number = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            base_url = f"https://wa.me/{clean_number}"
            
            if message:
                encoded_message = urllib.parse.quote(message)
                return f"{base_url}?text={encoded_message}"
            
            return base_url
            
        except Exception as e:
            logger.error(f"Error generating WhatsApp link: {str(e)}")
            return f"https://wa.me/{phone_number.replace('+', '')}"
    
    def validate_international_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        Validate international phone number format
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Dictionary with validation results and formatted numbers
        """
        try:
            formatted = self._format_international_number(phone_number)
            
            if not formatted:
                return {'valid': False, 'error': 'Invalid phone number format'}
            
            # Extract country code (first 1-3 digits after +)
            digits = formatted[1:]
            country_code = None
            
            # Common country code patterns
            if digits.startswith('1'):
                country_code = 'US'  # US/Canada
            elif digits.startswith('44'):
                country_code = 'UK'
            elif digits.startswith('61'):
                country_code = 'AU'
            elif digits.startswith('91'):
                country_code = 'IN'
            elif digits.startswith('49'):
                country_code = 'DE'
            elif digits.startswith('33'):
                country_code = 'FR'
            elif digits.startswith('81'):
                country_code = 'JP'
            elif digits.startswith('65'):
                country_code = 'SG'
            elif digits.startswith('55'):
                country_code = 'BR'
            
            return {
                'valid': True,
                'formatted': formatted,
                'country_code': country_code,
                'whatsapp_link': self.generate_whatsapp_link(formatted),
                'config': self.get_country_config(country_code) if country_code else None
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def get_international_examples(self) -> List[Dict[str, str]]:
        """Get example phone numbers for different countries"""
        return [
            {'country': 'United States', 'code': 'US', 'example': '+1-555-123-4567', 'format': '+1XXXXXXXXXX'},
            {'country': 'United Kingdom', 'code': 'UK', 'example': '+44-20-7123-4567', 'format': '+44XXXXXXXXXX'},
            {'country': 'Australia', 'code': 'AU', 'example': '+61-3-8123-4567', 'format': '+61XXXXXXXXX'},
            {'country': 'Canada', 'code': 'CA', 'example': '+1-416-123-4567', 'format': '+1XXXXXXXXXX'},
            {'country': 'India', 'code': 'IN', 'example': '+91-80-1234-5678', 'format': '+91XXXXXXXXXX'},
            {'country': 'Germany', 'code': 'DE', 'example': '+49-30-1234-5678', 'format': '+49XXXXXXXXXX'},
            {'country': 'France', 'code': 'FR', 'example': '+33-1-42-12-34-56', 'format': '+33XXXXXXXXX'},
            {'country': 'Japan', 'code': 'JP', 'example': '+81-3-1234-5678', 'format': '+81XXXXXXXXXX'},
            {'country': 'Singapore', 'code': 'SG', 'example': '+65-6123-4567', 'format': '+65XXXXXXXX'},
            {'country': 'Brazil', 'code': 'BR', 'example': '+55-11-1234-5678', 'format': '+55XXXXXXXXXXX'}
        ]
