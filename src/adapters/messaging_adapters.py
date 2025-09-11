"""
AWS End User Messaging adapter for messaging service.
"""

import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError

from ..core.interfaces import MessagingServiceInterface


class AWSMessagingService(MessagingServiceInterface):
    """AWS End User Messaging implementation."""
    
    def __init__(self, region: str = "us-east-1"):
        self.sns = boto3.client('sns', region_name=region)
        self.pinpoint = boto3.client('pinpoint', region_name=region)
    
    async def send_message(self, to: str, message: str) -> bool:
        """Send SMS message via AWS SNS."""
        try:
            response = self.sns.publish(
                PhoneNumber=to,
                Message=message
            )
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
        except ClientError as e:
            print(f"Error sending message to {to}: {e}")
            return False
    
    async def send_media(self, to: str, media_url: str, caption: str) -> bool:
        """Send media message (implementation depends on messaging platform)."""
        # For SMS, we'll send the caption with a link to the media
        message = f"{caption}\n\nView image: {media_url}"
        return await self.send_message(to, message)


class WhatsAppMessagingService(MessagingServiceInterface):
    """WhatsApp Business API implementation."""
    
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v18.0"
    
    async def send_message(self, to: str, message: str) -> bool:
        """Send WhatsApp message."""
        import aiohttp
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Error sending WhatsApp message to {to}: {e}")
            return False
    
    async def send_media(self, to: str, media_url: str, caption: str) -> bool:
        """Send WhatsApp media message."""
        import aiohttp
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {
                "link": media_url,
                "caption": caption
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Error sending WhatsApp media to {to}: {e}")
            return False
