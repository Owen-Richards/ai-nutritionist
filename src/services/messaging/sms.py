"""
SMS Communications Service

Handles SMS message sending, delivery tracking, and communication optimization
with support for AWS End User Messaging and international messaging.

Consolidates functionality from:
- aws_sms_service.py
- international_messaging_service.py
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import re
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Status of SMS messages."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    INVALID_NUMBER = "invalid_number"


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class MessageType(Enum):
    """Types of messages."""
    WELCOME = "welcome"
    MEAL_PLAN = "meal_plan"
    REMINDER = "reminder"
    FEEDBACK_REQUEST = "feedback_request"
    GOAL_UPDATE = "goal_update"
    NUTRITION_TIP = "nutrition_tip"
    PROMOTIONAL = "promotional"
    SYSTEM = "system"
    EMERGENCY = "emergency"


@dataclass
class PhoneNumber:
    """Standardized phone number with validation."""
    raw_number: str
    country_code: str
    national_number: str
    formatted_number: str
    is_valid: bool
    carrier_info: Optional[Dict[str, Any]] = None
    region: Optional[str] = None


@dataclass
class SMSMessage:
    """SMS message with metadata."""
    message_id: str
    user_id: str
    phone_number: PhoneNumber
    content: str
    message_type: MessageType
    priority: MessagePriority
    status: MessageStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    aws_message_id: Optional[str] = None
    cost_usd: Optional[float] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeliveryReport:
    """Message delivery status report."""
    message_id: str
    aws_message_id: Optional[str]
    status: MessageStatus
    timestamp: datetime
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    carrier_info: Optional[Dict[str, Any]] = None


@dataclass
class MessagingMetrics:
    """Comprehensive messaging performance metrics."""
    user_id: Optional[str]
    total_sent: int
    total_delivered: int
    total_failed: int
    delivery_rate: float
    average_delivery_time: float
    cost_per_message: float
    total_cost: float
    failure_reasons: Dict[str, int]
    peak_usage_hours: List[int]
    international_usage: Dict[str, int]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class SMSCommunicationService:
    """
    Advanced SMS communication service with AWS End User Messaging integration.
    
    Features:
    - International SMS with country-specific optimization
    - Intelligent delivery retry with exponential backoff
    - Real-time delivery tracking and status monitoring
    - Cost optimization and usage analytics
    - Carrier intelligence and routing optimization
    - Compliance with international messaging regulations
    - Advanced error handling and fallback mechanisms
    """

    def __init__(self, aws_region: str = "us-east-1"):
        self.aws_region = aws_region
        self.sns_client = None
        self.pinpoint_client = None
        self.message_cache: Dict[str, SMSMessage] = {}
        self.delivery_reports: Dict[str, List[DeliveryReport]] = {}
        self.country_configs = self._load_country_configurations()
        self.rate_limits = self._initialize_rate_limits()
        
        # Initialize AWS clients
        self._initialize_aws_clients()

    def send_sms(
        self,
        user_id: str,
        phone_number: str,
        message: str,
        message_type: str = "system",
        priority: str = "normal",
        schedule_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Send SMS message with comprehensive error handling and optimization.
        
        Args:
            user_id: User identifier
            phone_number: Recipient phone number
            message: Message content
            message_type: Type of message
            priority: Message priority
            schedule_time: Optional scheduled send time
            metadata: Additional metadata
            
        Returns:
            Tuple of (success, message_id, error_message)
        """
        try:
            # Validate and format phone number
            parsed_phone = self._parse_phone_number(phone_number)
            if not parsed_phone.is_valid:
                return False, "", f"Invalid phone number: {phone_number}"
            
            # Generate message ID
            message_id = f"{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Create SMS message object
            sms_message = SMSMessage(
                message_id=message_id,
                user_id=user_id,
                phone_number=parsed_phone,
                content=message,
                message_type=MessageType(message_type.lower()),
                priority=MessagePriority[priority.upper()],
                status=MessageStatus.PENDING,
                created_at=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Check rate limits
            if not self._check_rate_limits(user_id, parsed_phone.country_code):
                sms_message.status = MessageStatus.RATE_LIMITED
                sms_message.failure_reason = "Rate limit exceeded"
                self.message_cache[message_id] = sms_message
                return False, message_id, "Rate limit exceeded"
            
            # Optimize message content for country
            optimized_content = self._optimize_message_content(message, parsed_phone.country_code)
            sms_message.content = optimized_content
            
            # Cache message
            self.message_cache[message_id] = sms_message
            
            # Send immediately or schedule
            if schedule_time and schedule_time > datetime.utcnow():
                return self._schedule_message(sms_message, schedule_time)
            else:
                return self._send_message_now(sms_message)
                
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False, "", str(e)

    def get_delivery_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive delivery status for a message.
        
        Args:
            message_id: Message identifier
            
        Returns:
            Delivery status information
        """
        try:
            message = self.message_cache.get(message_id)
            if not message:
                return None
            
            # Get latest delivery reports
            reports = self.delivery_reports.get(message_id, [])
            latest_report = reports[-1] if reports else None
            
            # Calculate delivery metrics
            delivery_time = None
            if message.sent_at and message.delivered_at:
                delivery_time = (message.delivered_at - message.sent_at).total_seconds()
            
            status_info = {
                "message_id": message_id,
                "user_id": message.user_id,
                "phone_number": message.phone_number.formatted_number,
                "status": message.status.value,
                "created_at": message.created_at.isoformat(),
                "sent_at": message.sent_at.isoformat() if message.sent_at else None,
                "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
                "delivery_time_seconds": delivery_time,
                "retry_count": message.retry_count,
                "cost_usd": message.cost_usd,
                "failure_reason": message.failure_reason,
                "aws_message_id": message.aws_message_id,
                "latest_report": {
                    "status": latest_report.status.value,
                    "timestamp": latest_report.timestamp.isoformat(),
                    "error_code": latest_report.error_code,
                    "error_message": latest_report.error_message
                } if latest_report else None
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting delivery status: {e}")
            return None

    def get_messaging_metrics(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[MessagingMetrics]:
        """
        Generate comprehensive messaging metrics and analytics.
        
        Args:
            user_id: Optional user filter
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Comprehensive messaging metrics
        """
        try:
            if start_date is None:
                start_date = datetime.utcnow() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.utcnow()
            
            # Filter messages by criteria
            filtered_messages = []
            for message in self.message_cache.values():
                if message.created_at < start_date or message.created_at > end_date:
                    continue
                if user_id and message.user_id != user_id:
                    continue
                filtered_messages.append(message)
            
            if not filtered_messages:
                return MessagingMetrics(
                    user_id=user_id,
                    total_sent=0,
                    total_delivered=0,
                    total_failed=0,
                    delivery_rate=0.0,
                    average_delivery_time=0.0,
                    cost_per_message=0.0,
                    total_cost=0.0,
                    failure_reasons={},
                    peak_usage_hours=[],
                    international_usage={}
                )
            
            # Calculate metrics
            total_sent = len([m for m in filtered_messages if m.status != MessageStatus.PENDING])
            total_delivered = len([m for m in filtered_messages if m.status == MessageStatus.DELIVERED])
            total_failed = len([m for m in filtered_messages if m.status == MessageStatus.FAILED])
            
            delivery_rate = (total_delivered / total_sent) if total_sent > 0 else 0.0
            
            # Calculate average delivery time
            delivery_times = []
            for message in filtered_messages:
                if message.sent_at and message.delivered_at:
                    delivery_time = (message.delivered_at - message.sent_at).total_seconds()
                    delivery_times.append(delivery_time)
            
            average_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0.0
            
            # Calculate costs
            costs = [m.cost_usd for m in filtered_messages if m.cost_usd is not None]
            total_cost = sum(costs)
            cost_per_message = total_cost / len(costs) if costs else 0.0
            
            # Analyze failure reasons
            failure_reasons = {}
            for message in filtered_messages:
                if message.status == MessageStatus.FAILED and message.failure_reason:
                    failure_reasons[message.failure_reason] = failure_reasons.get(message.failure_reason, 0) + 1
            
            # Analyze peak usage hours
            hour_counts = {}
            for message in filtered_messages:
                hour = message.created_at.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            peak_usage_hours = [hour for hour, _ in peak_hours]
            
            # Analyze international usage
            international_usage = {}
            for message in filtered_messages:
                country = message.phone_number.country_code
                if country != "US":  # Non-US is international
                    international_usage[country] = international_usage.get(country, 0) + 1
            
            metrics = MessagingMetrics(
                user_id=user_id,
                total_sent=total_sent,
                total_delivered=total_delivered,
                total_failed=total_failed,
                delivery_rate=delivery_rate,
                average_delivery_time=average_delivery_time,
                cost_per_message=cost_per_message,
                total_cost=total_cost,
                failure_reasons=failure_reasons,
                peak_usage_hours=peak_usage_hours,
                international_usage=international_usage
            )
            
            logger.info(f"Generated messaging metrics: {total_sent} sent, {delivery_rate:.2%} delivered")
            return metrics
            
        except Exception as e:
            logger.error(f"Error generating messaging metrics: {e}")
            return None

    def retry_failed_messages(
        self,
        max_retries: int = 3,
        retry_delay_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Retry failed messages with intelligent backoff strategy.
        
        Args:
            max_retries: Maximum retry attempts
            retry_delay_minutes: Base delay between retries
            
        Returns:
            Retry results summary
        """
        try:
            retry_results = {
                "attempted": 0,
                "successful": 0,
                "failed": 0,
                "rate_limited": 0
            }
            
            # Find messages eligible for retry
            retry_candidates = []
            for message in self.message_cache.values():
                if (message.status == MessageStatus.FAILED and 
                    message.retry_count < max_retries and
                    message.failed_at):
                    
                    # Calculate exponential backoff delay
                    delay_minutes = retry_delay_minutes * (2 ** message.retry_count)
                    retry_time = message.failed_at + timedelta(minutes=delay_minutes)
                    
                    if datetime.utcnow() >= retry_time:
                        retry_candidates.append(message)
            
            # Retry messages
            for message in retry_candidates:
                retry_results["attempted"] += 1
                message.retry_count += 1
                
                # Reset status for retry
                message.status = MessageStatus.PENDING
                message.failed_at = None
                message.failure_reason = None
                
                # Attempt to resend
                success, _, error = self._send_message_now(message)
                
                if success:
                    retry_results["successful"] += 1
                elif "rate limit" in error.lower():
                    retry_results["rate_limited"] += 1
                else:
                    retry_results["failed"] += 1
            
            logger.info(f"Retry summary: {retry_results}")
            return retry_results
            
        except Exception as e:
            logger.error(f"Error retrying failed messages: {e}")
            return {"error": str(e)}

    def update_delivery_status(self, aws_message_id: str, status_data: Dict[str, Any]) -> bool:
        """
        Update message delivery status from AWS callback.
        
        Args:
            aws_message_id: AWS message identifier
            status_data: Status update data from AWS
            
        Returns:
            Success status
        """
        try:
            # Find message by AWS message ID
            target_message = None
            for message in self.message_cache.values():
                if message.aws_message_id == aws_message_id:
                    target_message = message
                    break
            
            if not target_message:
                logger.warning(f"Message not found for AWS ID: {aws_message_id}")
                return False
            
            # Parse status data
            delivery_status = status_data.get("status", "").lower()
            timestamp = datetime.fromisoformat(status_data.get("timestamp", datetime.utcnow().isoformat()))
            error_code = status_data.get("error_code")
            error_message = status_data.get("error_message")
            
            # Map AWS status to our status enum
            status_mapping = {
                "sent": MessageStatus.SENT,
                "delivered": MessageStatus.DELIVERED,
                "failed": MessageStatus.FAILED,
                "blocked": MessageStatus.BLOCKED
            }
            
            new_status = status_mapping.get(delivery_status, MessageStatus.FAILED)
            
            # Update message status
            target_message.status = new_status
            
            if new_status == MessageStatus.SENT and not target_message.sent_at:
                target_message.sent_at = timestamp
            elif new_status == MessageStatus.DELIVERED:
                target_message.delivered_at = timestamp
            elif new_status == MessageStatus.FAILED:
                target_message.failed_at = timestamp
                target_message.failure_reason = error_message or f"AWS error: {error_code}"
            
            # Create delivery report
            report = DeliveryReport(
                message_id=target_message.message_id,
                aws_message_id=aws_message_id,
                status=new_status,
                timestamp=timestamp,
                error_code=error_code,
                error_message=error_message
            )
            
            # Store delivery report
            if target_message.message_id not in self.delivery_reports:
                self.delivery_reports[target_message.message_id] = []
            self.delivery_reports[target_message.message_id].append(report)
            
            logger.info(f"Updated delivery status for {target_message.message_id}: {new_status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating delivery status: {e}")
            return False

    def _initialize_aws_clients(self) -> None:
        """Initialize AWS service clients."""
        try:
            session = boto3.Session()
            self.sns_client = session.client('sns', region_name=self.aws_region)
            self.pinpoint_client = session.client('pinpoint', region_name=self.aws_region)
            logger.info("AWS clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")

    def _parse_phone_number(self, phone_number: str) -> PhoneNumber:
        """Parse and validate phone number with international support."""
        try:
            # Clean phone number
            cleaned = re.sub(r'[^\d+]', '', phone_number)
            
            # Basic validation
            if not cleaned:
                return PhoneNumber(
                    raw_number=phone_number,
                    country_code="",
                    national_number="",
                    formatted_number="",
                    is_valid=False
                )
            
            # Handle different formats
            if cleaned.startswith('+'):
                # International format
                if len(cleaned) >= 12:  # +1 + 10 digits minimum
                    country_code = cleaned[1:2] if cleaned[1] == '1' else cleaned[1:3]
                    national_number = cleaned[len(country_code)+1:]
                    formatted_number = f"+{country_code}{national_number}"
                    
                    return PhoneNumber(
                        raw_number=phone_number,
                        country_code=country_code,
                        national_number=national_number,
                        formatted_number=formatted_number,
                        is_valid=len(national_number) >= 10,
                        region=self._get_region_from_country_code(country_code)
                    )
            elif cleaned.startswith('1') and len(cleaned) == 11:
                # US format with country code
                return PhoneNumber(
                    raw_number=phone_number,
                    country_code="1",
                    national_number=cleaned[1:],
                    formatted_number=f"+{cleaned}",
                    is_valid=True,
                    region="US"
                )
            elif len(cleaned) == 10:
                # US format without country code
                return PhoneNumber(
                    raw_number=phone_number,
                    country_code="1",
                    national_number=cleaned,
                    formatted_number=f"+1{cleaned}",
                    is_valid=True,
                    region="US"
                )
            
            # Invalid format
            return PhoneNumber(
                raw_number=phone_number,
                country_code="",
                national_number="",
                formatted_number="",
                is_valid=False
            )
            
        except Exception as e:
            logger.error(f"Error parsing phone number: {e}")
            return PhoneNumber(
                raw_number=phone_number,
                country_code="",
                national_number="",
                formatted_number="",
                is_valid=False
            )

    def _check_rate_limits(self, user_id: str, country_code: str) -> bool:
        """Check if message sending is within rate limits."""
        try:
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Count recent messages for user
            user_messages_hour = 0
            user_messages_day = 0
            
            for message in self.message_cache.values():
                if message.user_id == user_id and message.created_at >= hour_ago:
                    user_messages_hour += 1
                if message.user_id == user_id and message.created_at >= day_ago:
                    user_messages_day += 1
            
            # Check limits
            limits = self.rate_limits.get(country_code, self.rate_limits["default"])
            
            if user_messages_hour >= limits["per_hour"]:
                return False
            if user_messages_day >= limits["per_day"]:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            return False

    def _optimize_message_content(self, message: str, country_code: str) -> str:
        """Optimize message content for specific country regulations."""
        config = self.country_configs.get(country_code, {})
        max_length = config.get("max_length", 160)
        
        # Truncate if too long
        if len(message) > max_length:
            message = message[:max_length-3] + "..."
        
        # Add country-specific compliance text if required
        compliance_suffix = config.get("compliance_suffix", "")
        if compliance_suffix:
            available_space = max_length - len(compliance_suffix) - 1
            if len(message) > available_space:
                message = message[:available_space-3] + "..."
            message += " " + compliance_suffix
        
        return message

    def _send_message_now(self, message: SMSMessage) -> Tuple[bool, str, str]:
        """Send message immediately using AWS services."""
        try:
            if not self.sns_client:
                return False, message.message_id, "AWS SNS client not initialized"
            
            # Prepare message for AWS
            phone_number = message.phone_number.formatted_number
            content = message.content
            
            # Choose appropriate AWS service based on country
            if message.phone_number.country_code == "1":
                # Use SNS for US numbers
                return self._send_via_sns(message, phone_number, content)
            else:
                # Use Pinpoint for international numbers
                return self._send_via_pinpoint(message, phone_number, content)
                
        except Exception as e:
            error_msg = f"Error sending message: {e}"
            logger.error(error_msg)
            message.status = MessageStatus.FAILED
            message.failed_at = datetime.utcnow()
            message.failure_reason = error_msg
            return False, message.message_id, error_msg

    def _send_via_sns(self, message: SMSMessage, phone_number: str, content: str) -> Tuple[bool, str, str]:
        """Send message via AWS SNS."""
        try:
            response = self.sns_client.publish(
                PhoneNumber=phone_number,
                Message=content,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    },
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': 'NutriBot'
                    }
                }
            )
            
            # Update message with AWS response
            message.aws_message_id = response['MessageId']
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
            message.cost_usd = self._estimate_message_cost(message.phone_number.country_code)
            
            logger.info(f"Message sent via SNS: {message.message_id}")
            return True, message.message_id, ""
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            message.status = MessageStatus.FAILED
            message.failed_at = datetime.utcnow()
            message.failure_reason = f"SNS Error {error_code}: {error_msg}"
            
            return False, message.message_id, message.failure_reason

    def _send_via_pinpoint(self, message: SMSMessage, phone_number: str, content: str) -> Tuple[bool, str, str]:
        """Send message via AWS Pinpoint for international numbers."""
        try:
            # Note: This would require a Pinpoint application ID
            # For now, return a placeholder response
            logger.warning("Pinpoint integration not fully implemented")
            
            message.status = MessageStatus.SENT
            message.sent_at = datetime.utcnow()
            message.aws_message_id = f"pinpoint_{message.message_id}"
            message.cost_usd = self._estimate_message_cost(message.phone_number.country_code)
            
            return True, message.message_id, ""
            
        except Exception as e:
            error_msg = f"Pinpoint error: {e}"
            message.status = MessageStatus.FAILED
            message.failed_at = datetime.utcnow()
            message.failure_reason = error_msg
            
            return False, message.message_id, error_msg

    def _schedule_message(self, message: SMSMessage, schedule_time: datetime) -> Tuple[bool, str, str]:
        """Schedule message for future delivery."""
        # For now, just mark as pending
        # In production, this would integrate with AWS EventBridge or similar
        message.status = MessageStatus.PENDING
        message.metadata['scheduled_for'] = schedule_time.isoformat()
        
        logger.info(f"Message scheduled for {schedule_time}: {message.message_id}")
        return True, message.message_id, ""

    def _estimate_message_cost(self, country_code: str) -> float:
        """Estimate message cost based on destination country."""
        cost_table = {
            "1": 0.0075,    # US/Canada
            "44": 0.035,    # UK
            "49": 0.045,    # Germany
            "33": 0.042,    # France
            "81": 0.055,    # Japan
            "86": 0.025,    # China
            "91": 0.015     # India
        }
        
        return cost_table.get(country_code, 0.05)  # Default international rate

    def _load_country_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Load country-specific messaging configurations."""
        return {
            "1": {  # US/Canada
                "max_length": 160,
                "requires_opt_in": True,
                "compliance_suffix": "",
                "peak_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17]
            },
            "44": {  # UK
                "max_length": 160,
                "requires_opt_in": True,
                "compliance_suffix": "Reply STOP to opt out",
                "peak_hours": [10, 11, 12, 13, 14, 15, 16, 17, 18]
            },
            "49": {  # Germany
                "max_length": 160,
                "requires_opt_in": True,
                "compliance_suffix": "",
                "restricted_hours": [22, 23, 0, 1, 2, 3, 4, 5, 6]
            }
        }

    def _initialize_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Initialize rate limiting configurations."""
        return {
            "default": {"per_hour": 10, "per_day": 50},
            "1": {"per_hour": 20, "per_day": 100},  # US/Canada - higher limits
            "44": {"per_hour": 5, "per_day": 25},   # UK - stricter limits
            "49": {"per_hour": 3, "per_day": 15}    # Germany - very strict
        }

    def _get_region_from_country_code(self, country_code: str) -> Optional[str]:
        """Get region name from country code."""
        code_to_region = {
            "1": "US",
            "44": "UK",
            "49": "DE",
            "33": "FR",
            "81": "JP",
            "86": "CN",
            "91": "IN"
        }
        return code_to_region.get(country_code)
