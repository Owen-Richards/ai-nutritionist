"""
Spam Protection Handler for AWS SMS
Advanced protection against spam, abuse, and cost overruns
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')
ssm = boto3.client('ssm')

# Get table names from environment
RATE_LIMITS_TABLE = os.getenv('RATE_LIMITS_TABLE')
USER_REPUTATION_TABLE = os.getenv('USER_REPUTATION_TABLE')
BLOCKED_NUMBERS_TABLE = os.getenv('BLOCKED_NUMBERS_TABLE')

# Configuration
MAX_MESSAGES_PER_HOUR = int(os.getenv('MAX_MESSAGES_PER_HOUR', '10'))
MAX_MESSAGES_PER_DAY = int(os.getenv('MAX_MESSAGES_PER_DAY', '50'))
DAILY_COST_LIMIT = float(os.getenv('DAILY_COST_LIMIT', '50.0'))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

# Spam detection patterns
SPAM_PATTERNS = [
    r'\b(win|won|winner|prize|lottery|claim|free|urgent|act now)\b',
    r'\b(click here|call now|limited time|expires soon)\b',
    r'\b(congratulations|selected|chosen|qualified)\b',
    r'\$\d+\s*(million|thousand|k)',
    r'\b(viagra|casino|poker|gambling)\b',
    r'https?://[^\s]+',  # Suspicious URLs
    r'\b\d{10,}\b',      # Long number sequences (suspicious)
]

# Common spam keywords in multiple languages
SPAM_KEYWORDS = {
    'en': ['spam', 'scam', 'virus', 'malware', 'phishing', 'fake'],
    'es': ['estafa', 'virus', 'malware', 'falso'],
    'fr': ['arnaque', 'virus', 'malware', 'faux'],
}


class SpamProtectionService:
    """Advanced spam protection and cost control for SMS"""
    
    def __init__(self):
        self.rate_limits_table = dynamodb.Table(RATE_LIMITS_TABLE)
        self.user_reputation_table = dynamodb.Table(USER_REPUTATION_TABLE)
        self.blocked_numbers_table = dynamodb.Table(BLOCKED_NUMBERS_TABLE)
        
        # Compile spam patterns for efficiency
        self.spam_regex = re.compile('|'.join(SPAM_PATTERNS), re.IGNORECASE)
    
    def check_message_allowed(self, phone_number: str, message: str, country_code: str = None) -> Dict[str, Any]:
        """
        Comprehensive check if message should be processed
        
        Returns:
            Dict with 'allowed', 'reason', 'action', and 'metadata'
        """
        try:
            # 1. Check if number is blocked
            if self.is_number_blocked(phone_number):
                return {
                    'allowed': False,
                    'reason': 'number_blocked',
                    'action': 'reject',
                    'metadata': {'block_source': 'manual_block'}
                }
            
            # 2. Check rate limits
            rate_limit_result = self.check_rate_limits(phone_number)
            if not rate_limit_result['allowed']:
                return rate_limit_result
            
            # 3. Spam detection
            spam_score = self.calculate_spam_score(message, phone_number, country_code)
            if spam_score > 0.7:  # High confidence spam
                self.handle_spam_detection(phone_number, message, spam_score)
                return {
                    'allowed': False,
                    'reason': 'spam_detected',
                    'action': 'reject',
                    'metadata': {'spam_score': spam_score}
                }
            elif spam_score > 0.5:  # Medium confidence - flag for review
                return {
                    'allowed': True,
                    'reason': 'suspicious_content',
                    'action': 'flag_and_process',
                    'metadata': {'spam_score': spam_score}
                }
            
            # 4. Update user reputation
            self.update_user_reputation(phone_number, 'legitimate_message')
            
            # 5. Update rate limiting
            self.update_rate_limits(phone_number)
            
            return {
                'allowed': True,
                'reason': 'legitimate_message',
                'action': 'process',
                'metadata': {'spam_score': spam_score}
            }
            
        except Exception as e:
            logger.error(f"Error in spam protection check: {str(e)}")
            # Fail open for legitimate users
            return {
                'allowed': True,
                'reason': 'protection_error',
                'action': 'process',
                'metadata': {'error': str(e)}
            }
    
    def is_number_blocked(self, phone_number: str) -> bool:
        """Check if phone number is in blocked list"""
        try:
            response = self.blocked_numbers_table.get_item(
                Key={'phone_number': phone_number}
            )
            return 'Item' in response
        except Exception as e:
            logger.error(f"Error checking blocked numbers: {str(e)}")
            return False
    
    def check_rate_limits(self, phone_number: str) -> Dict[str, Any]:
        """Check hourly and daily rate limits"""
        try:
            current_time = int(time.time())
            hour_start = current_time - (current_time % 3600)  # Start of current hour
            day_start = current_time - (current_time % 86400)  # Start of current day
            
            # Get current rate limit data
            response = self.rate_limits_table.get_item(
                Key={'phone_number': phone_number}
            )
            
            if 'Item' not in response:
                # First message from this number
                return {'allowed': True, 'reason': 'new_user', 'action': 'process'}
            
            item = response['Item']
            hourly_count = item.get('hourly_count', 0)
            daily_count = item.get('daily_count', 0)
            last_hour = item.get('last_hour', 0)
            last_day = item.get('last_day', 0)
            
            # Reset counters if we're in a new time period
            if last_hour < hour_start:
                hourly_count = 0
            if last_day < day_start:
                daily_count = 0
            
            # Check limits
            if hourly_count >= MAX_MESSAGES_PER_HOUR:
                self.log_rate_limit_violation(phone_number, 'hourly', hourly_count)
                return {
                    'allowed': False,
                    'reason': 'hourly_rate_limit_exceeded',
                    'action': 'reject',
                    'metadata': {'count': hourly_count, 'limit': MAX_MESSAGES_PER_HOUR}
                }
            
            if daily_count >= MAX_MESSAGES_PER_DAY:
                self.log_rate_limit_violation(phone_number, 'daily', daily_count)
                return {
                    'allowed': False,
                    'reason': 'daily_rate_limit_exceeded',
                    'action': 'reject',
                    'metadata': {'count': daily_count, 'limit': MAX_MESSAGES_PER_DAY}
                }
            
            return {'allowed': True, 'reason': 'within_limits', 'action': 'process'}
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {str(e)}")
            return {'allowed': True, 'reason': 'rate_limit_error', 'action': 'process'}
    
    def calculate_spam_score(self, message: str, phone_number: str, country_code: str = None) -> float:
        """
        Calculate spam probability score (0-1)
        Higher score = more likely to be spam
        """
        score = 0.0
        factors = []
        
        # 1. Pattern matching
        if self.spam_regex.search(message):
            score += 0.4
            factors.append('spam_patterns')
        
        # 2. Keyword analysis
        message_lower = message.lower()
        for lang, keywords in SPAM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    score += 0.3
                    factors.append(f'spam_keyword_{lang}')
                    break
        
        # 3. Message characteristics
        if len(message) > 1000:  # Very long messages
            score += 0.2
            factors.append('long_message')
        
        if message.count('!') > 3:  # Excessive exclamation marks
            score += 0.1
            factors.append('excessive_punctuation')
        
        if message.isupper() and len(message) > 20:  # ALL CAPS
            score += 0.2
            factors.append('all_caps')
        
        # 4. Repetitive content detection
        words = message.split()
        if len(words) > 5:
            word_freq = defaultdict(int)
            for word in words:
                word_freq[word] += 1
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.4:  # >40% repetition
                score += 0.3
                factors.append('repetitive_content')
        
        # 5. User reputation factor
        reputation = self.get_user_reputation(phone_number)
        if reputation < 0.5:
            score += 0.2
            factors.append('low_reputation')
        elif reputation > 0.8:
            score -= 0.1  # Bonus for good reputation
            factors.append('good_reputation')
        
        # 6. Frequency analysis
        recent_messages = self.get_recent_message_count(phone_number, hours=1)
        if recent_messages > 5:
            score += 0.2
            factors.append('high_frequency')
        
        # 7. Geographic factors (if available)
        if country_code and self.is_high_risk_country(country_code):
            score += 0.1
            factors.append('high_risk_country')
        
        # Normalize score to 0-1 range
        score = min(score, 1.0)
        
        # Log spam detection details
        if score > 0.3:
            logger.info(f"Spam score {score:.2f} for {phone_number}: {factors}")
        
        return score
    
    def get_user_reputation(self, phone_number: str) -> float:
        """Get user reputation score (0-1, higher is better)"""
        try:
            response = self.user_reputation_table.get_item(
                Key={'phone_number': phone_number}
            )
            
            if 'Item' not in response:
                return 0.5  # Neutral reputation for new users
            
            item = response['Item']
            legitimate_count = item.get('legitimate_count', 0)
            spam_count = item.get('spam_count', 0)
            total_messages = legitimate_count + spam_count
            
            if total_messages == 0:
                return 0.5
            
            # Simple reputation calculation
            reputation = legitimate_count / total_messages
            
            # Apply time decay (older activity matters less)
            last_activity = item.get('last_activity', 0)
            days_since_activity = (time.time() - last_activity) / 86400
            time_factor = max(0.1, 1.0 - (days_since_activity * 0.1))
            
            return reputation * time_factor
            
        except Exception as e:
            logger.error(f"Error getting user reputation: {str(e)}")
            return 0.5
    
    def get_recent_message_count(self, phone_number: str, hours: int = 1) -> int:
        """Get number of messages from user in recent hours"""
        try:
            response = self.rate_limits_table.get_item(
                Key={'phone_number': phone_number}
            )
            
            if 'Item' not in response:
                return 0
            
            item = response['Item']
            current_time = int(time.time())
            time_threshold = current_time - (hours * 3600)
            
            # Count messages in the specified time window
            message_times = item.get('recent_message_times', [])
            recent_count = sum(1 for t in message_times if t > time_threshold)
            
            return recent_count
            
        except Exception as e:
            logger.error(f"Error getting recent message count: {str(e)}")
            return 0
    
    def is_high_risk_country(self, country_code: str) -> bool:
        """Check if country is considered high-risk for spam"""
        # This list should be maintained based on your spam analytics
        high_risk_countries = ['CN', 'RU', 'IN', 'PK', 'BD']  # Example list
        return country_code.upper() in high_risk_countries
    
    def update_rate_limits(self, phone_number: str):
        """Update rate limiting counters"""
        try:
            current_time = int(time.time())
            hour_start = current_time - (current_time % 3600)
            day_start = current_time - (current_time % 86400)
            
            # Get current data
            response = self.rate_limits_table.get_item(
                Key={'phone_number': phone_number}
            )
            
            if 'Item' in response:
                item = response['Item']
                hourly_count = item.get('hourly_count', 0)
                daily_count = item.get('daily_count', 0)
                last_hour = item.get('last_hour', 0)
                last_day = item.get('last_day', 0)
                recent_times = item.get('recent_message_times', [])
                
                # Reset counters if needed
                if last_hour < hour_start:
                    hourly_count = 0
                if last_day < day_start:
                    daily_count = 0
                
                # Clean up old message times (keep last 24 hours)
                cutoff_time = current_time - 86400
                recent_times = [t for t in recent_times if t > cutoff_time]
                recent_times.append(current_time)
                
            else:
                hourly_count = 0
                daily_count = 0
                recent_times = [current_time]
            
            # Update counters
            self.rate_limits_table.put_item(
                Item={
                    'phone_number': phone_number,
                    'hourly_count': hourly_count + 1,
                    'daily_count': daily_count + 1,
                    'last_hour': hour_start,
                    'last_day': day_start,
                    'recent_message_times': recent_times,
                    'last_updated': current_time,
                    'expires_at': current_time + 604800  # 7 days TTL
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating rate limits: {str(e)}")
    
    def update_user_reputation(self, phone_number: str, action: str):
        """Update user reputation based on their behavior"""
        try:
            current_time = int(time.time())
            
            response = self.user_reputation_table.get_item(
                Key={'phone_number': phone_number}
            )
            
            if 'Item' in response:
                item = response['Item']
                legitimate_count = item.get('legitimate_count', 0)
                spam_count = item.get('spam_count', 0)
            else:
                legitimate_count = 0
                spam_count = 0
            
            # Update counters based on action
            if action == 'legitimate_message':
                legitimate_count += 1
            elif action == 'spam_detected':
                spam_count += 1
            
            self.user_reputation_table.put_item(
                Item={
                    'phone_number': phone_number,
                    'legitimate_count': legitimate_count,
                    'spam_count': spam_count,
                    'last_activity': current_time,
                    'expires_at': current_time + 2592000  # 30 days TTL
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating user reputation: {str(e)}")
    
    def handle_spam_detection(self, phone_number: str, message: str, spam_score: float):
        """Handle detected spam"""
        try:
            # Update reputation
            self.update_user_reputation(phone_number, 'spam_detected')
            
            # Log spam detection
            logger.warning(f"SPAM DETECTED: {phone_number} (score: {spam_score:.2f}): {message[:100]}")
            
            # Send CloudWatch metric
            cloudwatch.put_metric_data(
                Namespace='AI-Nutritionist/SMS',
                MetricData=[
                    {
                        'MetricName': 'SpamMessagesDetected',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {
                                'Name': 'Environment',
                                'Value': ENVIRONMENT
                            }
                        ]
                    }
                ]
            )
            
            # Auto-block if spam score is very high or repeat offender
            if spam_score > 0.9 or self.is_repeat_spammer(phone_number):
                self.block_number(phone_number, 'auto_spam_detection', spam_score)
            
        except Exception as e:
            logger.error(f"Error handling spam detection: {str(e)}")
    
    def is_repeat_spammer(self, phone_number: str) -> bool:
        """Check if user is a repeat spam offender"""
        try:
            response = self.user_reputation_table.get_item(
                Key={'phone_number': phone_number}
            )
            
            if 'Item' not in response:
                return False
            
            item = response['Item']
            spam_count = item.get('spam_count', 0)
            legitimate_count = item.get('legitimate_count', 0)
            
            # Block if >80% spam and >3 spam messages
            total_messages = spam_count + legitimate_count
            if total_messages >= 4 and spam_count / total_messages > 0.8:
                return True
            
            # Block if >5 spam messages regardless of ratio
            if spam_count > 5:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking repeat spammer: {str(e)}")
            return False
    
    def block_number(self, phone_number: str, reason: str, spam_score: float = None):
        """Block a phone number"""
        try:
            current_time = int(time.time())
            
            self.blocked_numbers_table.put_item(
                Item={
                    'phone_number': phone_number,
                    'block_reason': reason,
                    'blocked_at': current_time,
                    'spam_score': spam_score,
                    'blocked_by': 'auto_system'
                }
            )
            
            logger.warning(f"BLOCKED NUMBER: {phone_number} - Reason: {reason}")
            
            # Send alert
            cloudwatch.put_metric_data(
                Namespace='AI-Nutritionist/SMS',
                MetricData=[
                    {
                        'MetricName': 'NumbersBlocked',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {
                                'Name': 'BlockReason',
                                'Value': reason
                            }
                        ]
                    }
                ]
            )
            
        except Exception as e:
            logger.error(f"Error blocking number: {str(e)}")
    
    def log_rate_limit_violation(self, phone_number: str, limit_type: str, count: int):
        """Log rate limit violations"""
        logger.warning(f"RATE LIMIT VIOLATION: {phone_number} - {limit_type} limit exceeded ({count} messages)")
        
        # Send CloudWatch metric
        cloudwatch.put_metric_data(
            Namespace='AI-Nutritionist/SMS',
            MetricData=[
                {
                    'MetricName': 'RateLimitViolations',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {
                            'Name': 'LimitType',
                            'Value': limit_type
                        }
                    ]
                }
            ]
        )


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for spam protection operations
    """
    try:
        action = event.get('action', 'check_message')
        spam_service = SpamProtectionService()
        
        if action == 'check_message':
            # Check if a message should be processed
            phone_number = event.get('phone_number')
            message = event.get('message')
            country_code = event.get('country_code')
            
            if not phone_number or not message:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing phone_number or message'})
                }
            
            result = spam_service.check_message_allowed(phone_number, message, country_code)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        
        elif action == 'daily_cost_analysis':
            # Triggered daily to analyze costs and adjust protections
            return perform_daily_cost_analysis()
        
        elif action == 'block_number':
            # Manual blocking
            phone_number = event.get('phone_number')
            reason = event.get('reason', 'manual_block')
            
            if not phone_number:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing phone_number'})
                }
            
            spam_service.block_number(phone_number, reason)
            
            return {
                'statusCode': 200,
                'body': json.dumps({'status': 'blocked', 'phone_number': phone_number})
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in spam protection handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def perform_daily_cost_analysis() -> Dict[str, Any]:
    """Perform daily cost analysis and adjust protections"""
    try:
        # This would analyze costs and adjust rate limits
        # Implementation would depend on your cost tracking setup
        
        logger.info("Performing daily cost analysis")
        
        # Example: Check if approaching cost limits and tighten restrictions
        # You would implement actual cost checking here
        
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'analysis_complete'})
        }
        
    except Exception as e:
        logger.error(f"Error in daily cost analysis: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
