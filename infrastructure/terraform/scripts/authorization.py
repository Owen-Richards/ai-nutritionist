#!/usr/bin/env python3
"""
Authorization and Rate Limiting Function
Validates users against whitelist and enforces usage limits
"""

import json
import boto3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    API Gateway authorizer function to validate users and enforce limits
    """
    try:
        # Extract phone number from request
        phone_number = extract_phone_number(event)
        if not phone_number:
            logger.warning("No phone number found in request")
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Check if user is authorized
        user_info = get_authorized_user(phone_number)
        if not user_info:
            logger.warning(f"Unauthorized phone number: {phone_number}")
            return generate_policy(phone_number, 'Deny', event['methodArn'])
        
        # Check daily usage limits
        current_usage = get_daily_usage(phone_number)
        daily_limit = int(user_info.get('daily_limit', 10))
        
        if current_usage >= daily_limit:
            logger.warning(f"Daily limit exceeded for {phone_number}: {current_usage}/{daily_limit}")
            return generate_policy(phone_number, 'Deny', event['methodArn'])
        
        # Check monthly usage limits
        monthly_usage = get_monthly_usage(phone_number)
        monthly_limit = int(user_info.get('monthly_limit', 100))
        
        if monthly_usage >= monthly_limit:
            logger.warning(f"Monthly limit exceeded for {phone_number}: {monthly_usage}/{monthly_limit}")
            return generate_policy(phone_number, 'Deny', event['methodArn'])
        
        # Update usage tracking
        update_usage_tracking(phone_number, user_info)
        
        # Generate allow policy with context
        policy = generate_policy(phone_number, 'Allow', event['methodArn'])
        policy['context'] = {
            'phone_number': phone_number,
            'user_name': user_info.get('user_name', 'Unknown'),
            'user_type': user_info.get('user_type', 'friend'),
            'daily_usage': str(current_usage + 1),
            'daily_limit': str(daily_limit),
            'monthly_usage': str(monthly_usage + 1),
            'monthly_limit': str(monthly_limit),
            'features_enabled': json.dumps(user_info.get('features_enabled', []))
        }
        
        logger.info(f"Authorized request for {phone_number}")
        return policy
        
    except Exception as e:
        logger.error(f"Authorization error: {str(e)}")
        return generate_policy('error', 'Deny', event.get('methodArn', '*'))

def extract_phone_number(event: Dict[str, Any]) -> Optional[str]:
    """Extract phone number from API Gateway event"""
    try:
        # Try query string first
        if 'queryStringParameters' in event and event['queryStringParameters']:
            phone = event['queryStringParameters'].get('phone')
            if phone:
                return normalize_phone_number(phone)
        
        # Try headers
        if 'headers' in event and event['headers']:
            phone = event['headers'].get('X-Phone-Number')
            if phone:
                return normalize_phone_number(phone)
        
        # Try request body for webhook
        if 'body' in event and event['body']:
            try:
                body = json.loads(event['body'])
                if 'From' in body:  # Twilio/WhatsApp format
                    return normalize_phone_number(body['From'])
                if 'phone' in body:
                    return normalize_phone_number(body['phone'])
            except json.JSONDecodeError:
                pass
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting phone number: {str(e)}")
        return None

def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to consistent format"""
    # Remove all non-numeric characters except +
    normalized = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Ensure it starts with +
    if not normalized.startswith('+'):
        normalized = '+' + normalized
    
    return normalized

def get_authorized_user(phone_number: str) -> Optional[Dict[str, Any]]:
    """Check if phone number is in authorized users table"""
    try:
        table_name = os.getenv('AUTHORIZED_USERS_TABLE')
        table = dynamodb.Table(table_name)
        
        response = table.get_item(
            Key={'phone_number': phone_number}
        )
        
        if 'Item' not in response:
            return None
        
        user = response['Item']
        
        # Check if user is active
        if not user.get('is_active', False):
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Error checking authorized user: {str(e)}")
        return None

def get_daily_usage(phone_number: str) -> int:
    """Get current daily usage for phone number"""
    try:
        table_name = os.getenv('USAGE_TRACKING_TABLE')
        table = dynamodb.Table(table_name)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = table.get_item(
            Key={
                'user_phone': phone_number,
                'date': today
            }
        )
        
        if 'Item' not in response:
            return 0
        
        return int(response['Item'].get('message_count', 0))
        
    except Exception as e:
        logger.error(f"Error getting daily usage: {str(e)}")
        return 0

def get_monthly_usage(phone_number: str) -> int:
    """Get current monthly usage for phone number"""
    try:
        table_name = os.getenv('USAGE_TRACKING_TABLE')
        table = dynamodb.Table(table_name)
        
        # Get all days in current month
        now = datetime.now()
        start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
        
        response = table.query(
            KeyConditionExpression='user_phone = :phone AND #date >= :start_date',
            ExpressionAttributeNames={
                '#date': 'date'
            },
            ExpressionAttributeValues={
                ':phone': phone_number,
                ':start_date': start_of_month
            }
        )
        
        total_usage = 0
        for item in response['Items']:
            total_usage += int(item.get('message_count', 0))
        
        return total_usage
        
    except Exception as e:
        logger.error(f"Error getting monthly usage: {str(e)}")
        return 0

def update_usage_tracking(phone_number: str, user_info: Dict[str, Any]):
    """Update usage tracking for the current request"""
    try:
        table_name = os.getenv('USAGE_TRACKING_TABLE')
        table = dynamodb.Table(table_name)
        
        today = datetime.now().strftime('%Y-%m-%d')
        now_timestamp = datetime.now().isoformat()
        
        # TTL for 90 days from now
        ttl = int((datetime.now() + timedelta(days=90)).timestamp())
        
        # Increment message count for today
        response = table.update_item(
            Key={
                'user_phone': phone_number,
                'date': today
            },
            UpdateExpression='ADD message_count :inc SET last_request = :timestamp, user_name = :name, ttl = :ttl',
            ExpressionAttributeValues={
                ':inc': 1,
                ':timestamp': now_timestamp,
                ':name': user_info.get('user_name', 'Unknown'),
                ':ttl': ttl
            },
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f"Updated usage for {phone_number}: {response['Attributes']['message_count']}")
        
    except Exception as e:
        logger.error(f"Error updating usage tracking: {str(e)}")

def generate_policy(principal_id: str, effect: str, resource: str) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway"""
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    return policy

def check_feature_access(user_info: Dict[str, Any], feature: str) -> bool:
    """Check if user has access to specific feature"""
    features_enabled = user_info.get('features_enabled', [])
    return feature in features_enabled or 'all' in features_enabled

# Additional utility functions for cost control

def get_current_monthly_spend() -> float:
    """Get current monthly spend for the project (simplified)"""
    # This would integrate with Cost Explorer API
    # For now, return 0 as placeholder
    return 0.0

def check_budget_threshold() -> Tuple[bool, float]:
    """Check if we're approaching budget threshold"""
    # This would check against AWS Budgets API
    # For now, return safe values
    return False, 0.0

def log_usage_metrics(phone_number: str, feature: str, cost_estimate: float):
    """Log usage metrics for cost tracking"""
    logger.info(f"Usage: {phone_number} used {feature}, estimated cost: ${cost_estimate:.4f}")

def get_user_cost_summary(phone_number: str) -> Dict[str, float]:
    """Get cost summary for a specific user"""
    # This would aggregate costs by user
    return {
        'daily_cost': 0.0,
        'monthly_cost': 0.0,
        'total_cost': 0.0
    }
