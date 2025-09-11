"""
AWS End User Messaging Service
Handles both SMS and WhatsApp messaging through AWS native APIs
"""

import json
import logging
import os
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSMessagingService:
    """Service for sending SMS and WhatsApp messages via AWS End User Messaging"""
    
    def __init__(self):
        self.sms_client = boto3.client('pinpoint-sms-voice-v2')
        self.whatsapp_client = boto3.client('pinpoint')  # For WhatsApp via Pinpoint
        self.ssm = boto3.client('ssm')
        self.sqs = boto3.client('sqs')
        
        # Get configuration from environment variables
        self.phone_pool_id = os.getenv('PHONE_POOL_ID')
        self.configuration_set = os.getenv('SMS_CONFIG_SET')
        self.whatsapp_application_id = os.getenv('WHATSAPP_APPLICATION_ID')  # New for WhatsApp
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self._origination_number = None
        self._whatsapp_number = None
        
        # International messaging support
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

    def send_whatsapp_message(self, to_number: str, message: str, country_code: str = None) -> Dict[str, Any]:
        """
        Send WhatsApp message using AWS End User Messaging (Pinpoint)
        
        Args:
            to_number: Phone number in international format (+1234567890)
            message: Message text
            country_code: Optional country code for localization
            
        Returns:
            Dict with success status and message ID
        """
        try:
            # Validate and format phone number
            formatted_number = self._format_international_number(to_number)
            if not formatted_number:
                return {'success': False, 'error': f'Invalid phone number format: {to_number}'}
            
            # Get WhatsApp origination number
            whatsapp_number = self._get_whatsapp_number()
            if not whatsapp_number:
                return {'success': False, 'error': 'No WhatsApp number configured'}
            
            # Send WhatsApp message via Pinpoint
            response = self.whatsapp_client.send_messages(
                ApplicationId=self.whatsapp_application_id,
                MessageRequest={
                    'Addresses': {
                        formatted_number: {
                            'ChannelType': 'CUSTOM'  # WhatsApp uses custom channel
                        }
                    },
                    'MessageConfiguration': {
                        'DefaultMessage': {
                            'Body': message
                        },
                        'CustomMessage': {
                            'Data': json.dumps({
                                'messaging_product': 'whatsapp',
                                'to': formatted_number.replace('+', ''),  # WhatsApp format
                                'type': 'text',
                                'text': {'body': message}
                            })
                        }
                    }
                }
            )
            
            logger.info(f"WhatsApp message sent successfully to {formatted_number}: {response['MessageResponse']['RequestId']}")
            
            return {
                'success': True,
                'message_id': response['MessageResponse']['RequestId'],
                'destination': formatted_number,
                'status': 'sent',
                'platform': 'whatsapp'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS WhatsApp error ({error_code}): {error_message}")
            
            return {
                'success': False,
                'error': f'AWS WhatsApp error: {error_message}',
                'error_code': error_code
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {to_number}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_sms(self, to_number: str, message: str, country_code: str = None) -> Dict[str, Any]:
        """
        Send SMS message using AWS End User Messaging
        
        Args:
            to_number: Phone number in international format (+1234567890)
            message: Message text
            country_code: Optional country code for localization
            
        Returns:
            Dict with success status and message ID
        """
        try:
            # Validate and format phone number
            formatted_number = self._format_international_number(to_number)
            if not formatted_number:
                return {'success': False, 'error': f'Invalid phone number format: {to_number}'}
            
            # Get origination number from pool
            origination_number = self._get_origination_number()
            if not origination_number:
                return {'success': False, 'error': 'No origination number available'}
            
            # Send SMS via AWS
            response = self.sms_client.send_text_message(
                DestinationPhoneNumber=formatted_number,
                OriginationIdentity=origination_number,
                MessageBody=message,
                ConfigurationSetName=self.configuration_set,
                MessageType='TRANSACTIONAL',
                DryRun=False
            )
            
            logger.info(f"SMS sent successfully to {formatted_number}: {response['MessageId']}")
            
            return {
                'success': True,
                'message_id': response['MessageId'],
                'destination': formatted_number,
                'status': 'sent'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS SMS error ({error_code}): {error_message}")
            
            return {
                'success': False,
                'error': f'AWS SMS error: {error_message}',
                'error_code': error_code
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_inbound_message(self, sqs_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process inbound SMS message from SQS
        
        Args:
            sqs_record: SQS record containing SMS event data
            
        Returns:
            Parsed message data or None if parsing fails
        """
        try:
            # Parse SQS message body
            message_body = json.loads(sqs_record['body'])
            
            # Extract SMS details from AWS event
            if 'Records' in message_body:
                # SNS-wrapped message
                sns_record = message_body['Records'][0]
                sms_data = json.loads(sns_record['Sns']['Message'])
            else:
                # Direct SQS message
                sms_data = message_body
            
            # Extract key information
            parsed_message = {
                'platform': 'aws_sms',
                'user_id': sms_data.get('originationPhoneNumber', ''),
                'message': sms_data.get('messageBody', ''),
                'destination_number': sms_data.get('destinationPhoneNumber', ''),
                'message_id': sms_data.get('messageId', ''),
                'timestamp': sms_data.get('timestamp', datetime.utcnow().isoformat()),
                'country_code': self._detect_country_from_number(sms_data.get('originationPhoneNumber', '')),
                'raw_data': sms_data
            }
            
            logger.info(f"Processed inbound SMS from {parsed_message['user_id']}: {parsed_message['message'][:50]}...")
            return parsed_message
            
        except Exception as e:
            logger.error(f"Error processing inbound SMS: {str(e)}")
            return None

    def send_bulk_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Send multiple SMS messages efficiently
        
        Args:
            messages: List of dicts with 'to_number' and 'message' keys
            
        Returns:
            Summary of sent messages
        """
        results = {
            'success_count': 0,
            'failure_count': 0,
            'results': []
        }
        
        for msg in messages:
            result = self.send_message(msg['to_number'], msg['message'], msg.get('country_code'))
            results['results'].append(result)
            
            if result['success']:
                results['success_count'] += 1
            else:
                results['failure_count'] += 1
        
        logger.info(f"Bulk SMS completed: {results['success_count']} sent, {results['failure_count']} failed")
        return results

    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Check delivery status of a sent message
        
        Args:
            message_id: AWS message ID
            
        Returns:
            Delivery status information
        """
        try:
            # AWS End User Messaging provides delivery events via CloudWatch
            # This would typically be implemented with CloudWatch Events
            # For now, return a placeholder
            return {
                'message_id': message_id,
                'status': 'delivered',  # Would be retrieved from CloudWatch Events
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking delivery status for {message_id}: {str(e)}")
            return {'error': str(e)}

    def handle_opt_out(self, phone_number: str) -> bool:
        """
        Handle opt-out requests (STOP messages)
        
        Args:
            phone_number: Phone number to opt out
            
        Returns:
            Success status
        """
        try:
            # Add to AWS opt-out list
            self.sms_client.put_opted_out_number(
                OptOutListName=f'ai-nutritionist-{self.environment}-optout-list',
                OptedOutNumber=phone_number
            )
            
            logger.info(f"Added {phone_number} to opt-out list")
            return True
            
        except Exception as e:
            logger.error(f"Error handling opt-out for {phone_number}: {str(e)}")
            return False

    def validate_international_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        Validate and format international phone number
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Validation result with formatted number and country info
        """
        try:
            formatted = self._format_international_number(phone_number)
            if not formatted:
                return {'valid': False, 'error': 'Invalid phone number format'}
            
            country_code = self._detect_country_from_number(formatted)
            config = self.get_country_config(country_code) if country_code else None
            
            return {
                'valid': True,
                'formatted': formatted,
                'country_code': country_code,
                'config': config,
                'whatsapp_link': self.generate_whatsapp_link(formatted)
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    def get_country_config(self, country_code: str) -> Dict[str, Any]:
        """Get localized configuration for country"""
        return self.COUNTRY_CONFIGS.get(country_code.upper(), self.COUNTRY_CONFIGS['US'])

    def _get_origination_number(self) -> Optional[str]:
        """Get origination phone number from the pool"""
        if self._origination_number:
            return self._origination_number
            
        try:
            if self.phone_pool_id:
                # Get phone numbers from pool
                response = self.sms_client.describe_phone_numbers(
                    Filters=[
                        {
                            'Name': 'pool-id',
                            'Values': [self.phone_pool_id]
                        }
                    ]
                )
                
                if response['PhoneNumbers']:
                    self._origination_number = response['PhoneNumbers'][0]['PhoneNumber']
                    return self._origination_number
            
            # Fallback: get from parameter store
            parameter_name = f'/ai-nutritionist/{self.environment}/sms/phone-number'
            response = self.ssm.get_parameter(Name=parameter_name)
            self._origination_number = response['Parameter']['Value']
            return self._origination_number
            
        except Exception as e:
            logger.error(f"Error getting origination number: {str(e)}")
            return None

    def _format_international_number(self, phone_number: str) -> Optional[str]:
        """Format phone number to international format"""
        try:
            # Remove all non-digit characters except +
            cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
            
            # Add + if not present and starts with country code
            if not cleaned.startswith('+'):
                if cleaned.startswith('1') and len(cleaned) == 11:  # US/Canada
                    cleaned = f'+{cleaned}'
                elif cleaned.startswith('44') and len(cleaned) >= 10:  # UK
                    cleaned = f'+{cleaned}'
                elif len(cleaned) >= 10:  # Other international
                    cleaned = f'+{cleaned}'
                else:
                    return None
            
            # Basic validation
            if len(cleaned) < 8 or len(cleaned) > 17:
                return None
                
            return cleaned
            
        except Exception:
            return None

    def _detect_country_from_number(self, phone_number: str) -> Optional[str]:
        """Detect country code from phone number"""
        if not phone_number:
            return None
            
        # Remove + and get first few digits
        digits = phone_number.replace('+', '')
        
        if digits.startswith('1'):
            return 'US'
        elif digits.startswith('44'):
            return 'UK'
        elif digits.startswith('61'):
            return 'AU'
        elif digits.startswith('91'):
            return 'IN'
        elif digits.startswith('49'):
            return 'DE'
        elif digits.startswith('33'):
            return 'FR'
        elif digits.startswith('81'):
            return 'JP'
        elif digits.startswith('65'):
            return 'SG'
        elif digits.startswith('55'):
            return 'BR'
        
        return None

    def get_international_examples(self) -> List[Dict[str, str]]:
        """Get example phone numbers for different countries"""
        return [
            {'country': 'United States', 'code': 'US', 'example': '+1-555-123-4567', 'format': '+15551234567'},
            {'country': 'United Kingdom', 'code': 'UK', 'example': '+44-20-7123-4567', 'format': '+442071234567'},
            {'country': 'Australia', 'code': 'AU', 'example': '+61-3-8123-4567', 'format': '+61381234567'},
            {'country': 'Canada', 'code': 'CA', 'example': '+1-416-123-4567', 'format': '+14161234567'},
            {'country': 'India', 'code': 'IN', 'example': '+91-80-1234-5678', 'format': '+918012345678'},
            {'country': 'Germany', 'code': 'DE', 'example': '+49-30-1234-5678', 'format': '+493012345678'},
            {'country': 'France', 'code': 'FR', 'example': '+33-1-42-12-34-56', 'format': '+33142123456'},
            {'country': 'Japan', 'code': 'JP', 'example': '+81-3-1234-5678', 'format': '+81312345678'},
            {'country': 'Singapore', 'code': 'SG', 'example': '+65-6123-4567', 'format': '+6561234567'},
            {'country': 'Brazil', 'code': 'BR', 'example': '+55-11-1234-5678', 'format': '+5511123456678'}
        ]

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
            import urllib.parse
            
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


# Factory function to get the appropriate messaging service  
def get_messaging_service() -> AWSMessagingService:
    """
    Factory function to get AWS messaging service instance
    Handles both SMS and WhatsApp through AWS End User Messaging
    """
    return AWSMessagingService()

# Backward compatibility aliases
def get_sms_service() -> AWSMessagingService:
    """Backward compatibility - now returns unified messaging service"""
    return get_messaging_service()
