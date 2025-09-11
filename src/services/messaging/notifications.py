"""
Notification Management Service

Handles intelligent notification scheduling, delivery optimization, and user
engagement management with respect for user preferences and behavior patterns.

Consolidates functionality from:
- notification_service.py
- engagement_optimization_service.py
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import uuid
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    MEAL_REMINDER = "meal_reminder"
    GOAL_UPDATE = "goal_update"
    WEEKLY_SUMMARY = "weekly_summary"
    MOTIVATIONAL = "motivational"
    EDUCATIONAL = "educational"
    SYSTEM_ALERT = "system_alert"
    PROMOTIONAL = "promotional"
    FEEDBACK_REQUEST = "feedback_request"
    ACHIEVEMENT = "achievement"
    CHECK_IN = "check_in"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class NotificationStatus(Enum):
    """Status of notifications."""
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    CLICKED = "clicked"
    DISMISSED = "dismissed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryChannel(Enum):
    """Available delivery channels."""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


@dataclass
class NotificationPreferences:
    """User's notification preferences."""
    user_id: str
    enabled_types: Set[NotificationType]
    quiet_hours: Tuple[int, int]  # (start_hour, end_hour)
    preferred_channels: Dict[NotificationType, List[DeliveryChannel]]
    frequency_limits: Dict[str, int]  # daily, weekly limits
    timezone: str
    language: str = "en"
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationSchedule:
    """Scheduled notification definition."""
    schedule_id: str
    user_id: str
    notification_type: NotificationType
    title: str
    content: str
    priority: NotificationPriority
    delivery_channel: DeliveryChannel
    scheduled_time: datetime
    created_time: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None
    personalization_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationDelivery:
    """Notification delivery record."""
    delivery_id: str
    schedule_id: str
    user_id: str
    notification_type: NotificationType
    status: NotificationStatus
    delivery_channel: DeliveryChannel
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    engagement_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngagementMetrics:
    """User engagement metrics for optimization."""
    user_id: str
    total_sent: int
    total_delivered: int
    total_read: int
    total_clicked: int
    delivery_rate: float
    read_rate: float
    click_rate: float
    optimal_times: List[int]  # Hours of day
    preferred_frequency: int  # Per week
    engagement_trend: str  # increasing, stable, decreasing
    last_engagement: datetime
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OptimizationRecommendation:
    """Recommendation for notification optimization."""
    user_id: str
    recommendation_type: str
    description: str
    expected_improvement: float
    confidence: float
    implementation_difficulty: str
    suggested_actions: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


class NotificationManagementService:
    """
    Advanced notification management service with intelligent optimization.
    
    Features:
    - Intelligent scheduling based on user behavior patterns
    - Multi-channel delivery optimization and fallback handling
    - Frequency capping and engagement-based throttling
    - Personalized quiet hours and preference management
    - A/B testing framework for notification optimization
    - Real-time engagement tracking and adaptation
    - Predictive analytics for optimal timing and content
    """

    def __init__(self):
        self.user_preferences: Dict[str, NotificationPreferences] = {}
        self.scheduled_notifications: Dict[str, NotificationSchedule] = {}
        self.delivery_records: Dict[str, List[NotificationDelivery]] = defaultdict(list)
        self.engagement_metrics: Dict[str, EngagementMetrics] = {}
        self.optimization_cache: Dict[str, List[OptimizationRecommendation]] = defaultdict(list)
        
        # Initialize default configurations
        self.default_preferences = self._initialize_default_preferences()
        self.channel_reliability = self._initialize_channel_reliability()

    def schedule_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        content: str,
        delivery_time: Optional[datetime] = None,
        priority: str = "normal",
        channel: Optional[str] = None,
        template_id: Optional[str] = None,
        personalization_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Schedule intelligent notification with optimization and preference checking.
        
        Args:
            user_id: User identifier
            notification_type: Type of notification
            title: Notification title
            content: Notification content
            delivery_time: When to deliver (None for immediate)
            priority: Priority level
            channel: Preferred delivery channel
            template_id: Optional template identifier
            personalization_data: Data for personalization
            metadata: Additional metadata
            
        Returns:
            Tuple of (success, schedule_id, error_message)
        """
        try:
            # Parse enums
            notif_type = NotificationType(notification_type.lower())
            priority_enum = NotificationPriority[priority.upper()]
            
            # Get user preferences
            preferences = self._get_user_preferences(user_id)
            
            # Check if user has this notification type enabled
            if notif_type not in preferences.enabled_types:
                return False, "", f"User has disabled {notification_type} notifications"
            
            # Determine optimal delivery channel
            if channel:
                delivery_channel = DeliveryChannel(channel.lower())
            else:
                delivery_channel = self._select_optimal_channel(user_id, notif_type, priority_enum)
            
            # Optimize delivery time
            if delivery_time is None:
                delivery_time = datetime.utcnow()
            
            optimized_time = self._optimize_delivery_time(user_id, notif_type, delivery_time, preferences)
            
            # Check frequency limits
            if not self._check_frequency_limits(user_id, notif_type, preferences):
                return False, "", "Frequency limit exceeded for this notification type"
            
            # Generate schedule ID
            schedule_id = str(uuid.uuid4())
            
            # Create notification schedule
            schedule = NotificationSchedule(
                schedule_id=schedule_id,
                user_id=user_id,
                notification_type=notif_type,
                title=title,
                content=content,
                priority=priority_enum,
                delivery_channel=delivery_channel,
                scheduled_time=optimized_time,
                created_time=datetime.utcnow(),
                template_id=template_id,
                personalization_data=personalization_data or {},
                metadata=metadata or {}
            )
            
            # Set expiration for non-urgent notifications
            if priority_enum != NotificationPriority.URGENT:
                schedule.expires_at = optimized_time + timedelta(hours=24)
            
            # Store schedule
            self.scheduled_notifications[schedule_id] = schedule
            
            logger.info(f"Scheduled notification {schedule_id} for user {user_id} at {optimized_time}")
            return True, schedule_id, None
            
        except Exception as e:
            logger.error(f"Error scheduling notification: {e}")
            return False, "", str(e)

    def send_notification(self, schedule_id: str) -> Tuple[bool, Optional[str]]:
        """
        Send scheduled notification with delivery tracking.
        
        Args:
            schedule_id: Scheduled notification identifier
            
        Returns:
            Tuple of (success, delivery_id)
        """
        try:
            schedule = self.scheduled_notifications.get(schedule_id)
            if not schedule:
                return False, None
            
            # Check if notification has expired
            if schedule.expires_at and datetime.utcnow() > schedule.expires_at:
                logger.warning(f"Notification {schedule_id} has expired")
                return False, None
            
            # Generate delivery ID
            delivery_id = str(uuid.uuid4())
            
            # Create delivery record
            delivery = NotificationDelivery(
                delivery_id=delivery_id,
                schedule_id=schedule_id,
                user_id=schedule.user_id,
                notification_type=schedule.notification_type,
                status=NotificationStatus.SENT,
                delivery_channel=schedule.delivery_channel,
                sent_at=datetime.utcnow()
            )
            
            # Attempt delivery through selected channel
            success, error_message = self._deliver_via_channel(schedule, delivery)
            
            if success:
                delivery.status = NotificationStatus.DELIVERED
                delivery.delivered_at = datetime.utcnow()
            else:
                delivery.status = NotificationStatus.FAILED
                delivery.failed_at = datetime.utcnow()
                delivery.failure_reason = error_message
                
                # Try fallback channel if available
                fallback_success = self._try_fallback_delivery(schedule, delivery)
                if fallback_success:
                    delivery.status = NotificationStatus.DELIVERED
                    delivery.delivered_at = datetime.utcnow()
                    success = True
            
            # Store delivery record
            self.delivery_records[schedule.user_id].append(delivery)
            
            # Update engagement metrics
            self._update_engagement_metrics(schedule.user_id)
            
            logger.info(f"Notification delivery {delivery_id}: {'success' if success else 'failed'}")
            return success, delivery_id
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False, None

    def track_engagement(
        self,
        delivery_id: str,
        engagement_type: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track user engagement with notifications.
        
        Args:
            delivery_id: Delivery record identifier
            engagement_type: Type of engagement (read, clicked, dismissed)
            timestamp: When engagement occurred
            metadata: Additional engagement data
            
        Returns:
            Success status
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Find delivery record
            delivery_record = None
            user_id = None
            
            for uid, deliveries in self.delivery_records.items():
                for delivery in deliveries:
                    if delivery.delivery_id == delivery_id:
                        delivery_record = delivery
                        user_id = uid
                        break
                if delivery_record:
                    break
            
            if not delivery_record:
                logger.warning(f"Delivery record not found: {delivery_id}")
                return False
            
            # Update delivery record based on engagement type
            engagement_type = engagement_type.lower()
            
            if engagement_type == "read":
                delivery_record.status = NotificationStatus.READ
                delivery_record.read_at = timestamp
            elif engagement_type == "clicked":
                delivery_record.status = NotificationStatus.CLICKED
                delivery_record.clicked_at = timestamp
                if not delivery_record.read_at:
                    delivery_record.read_at = timestamp  # Implies read
            elif engagement_type == "dismissed":
                delivery_record.status = NotificationStatus.DISMISSED
            
            # Calculate engagement score
            delivery_record.engagement_score = self._calculate_engagement_score(delivery_record)
            
            # Update metadata
            if metadata:
                delivery_record.metadata.update(metadata)
            
            # Update user engagement metrics
            self._update_engagement_metrics(user_id)
            
            # Trigger optimization if needed
            self._trigger_optimization_if_needed(user_id)
            
            logger.info(f"Tracked engagement: {delivery_id} - {engagement_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking engagement: {e}")
            return False

    def update_user_preferences(
        self,
        user_id: str,
        preferences_data: Dict[str, Any]
    ) -> bool:
        """
        Update user notification preferences with validation.
        
        Args:
            user_id: User identifier
            preferences_data: Updated preference data
            
        Returns:
            Success status
        """
        try:
            current_prefs = self._get_user_preferences(user_id)
            
            # Update enabled types
            if 'enabled_types' in preferences_data:
                enabled_types = set()
                for notif_type in preferences_data['enabled_types']:
                    try:
                        enabled_types.add(NotificationType(notif_type.lower()))
                    except ValueError:
                        logger.warning(f"Invalid notification type: {notif_type}")
                current_prefs.enabled_types = enabled_types
            
            # Update quiet hours
            if 'quiet_hours' in preferences_data:
                quiet_hours = preferences_data['quiet_hours']
                if isinstance(quiet_hours, list) and len(quiet_hours) == 2:
                    start_hour, end_hour = quiet_hours
                    if 0 <= start_hour <= 23 and 0 <= end_hour <= 23:
                        current_prefs.quiet_hours = (start_hour, end_hour)
            
            # Update preferred channels
            if 'preferred_channels' in preferences_data:
                preferred_channels = {}
                for notif_type, channels in preferences_data['preferred_channels'].items():
                    try:
                        type_enum = NotificationType(notif_type.lower())
                        channel_enums = []
                        for channel in channels:
                            try:
                                channel_enums.append(DeliveryChannel(channel.lower()))
                            except ValueError:
                                logger.warning(f"Invalid delivery channel: {channel}")
                        if channel_enums:
                            preferred_channels[type_enum] = channel_enums
                    except ValueError:
                        logger.warning(f"Invalid notification type: {notif_type}")
                current_prefs.preferred_channels = preferred_channels
            
            # Update frequency limits
            if 'frequency_limits' in preferences_data:
                frequency_limits = preferences_data['frequency_limits']
                if isinstance(frequency_limits, dict):
                    current_prefs.frequency_limits = frequency_limits
            
            # Update timezone
            if 'timezone' in preferences_data:
                current_prefs.timezone = preferences_data['timezone']
            
            # Update language
            if 'language' in preferences_data:
                current_prefs.language = preferences_data['language']
            
            current_prefs.last_updated = datetime.utcnow()
            self.user_preferences[user_id] = current_prefs
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False

    def get_engagement_insights(
        self,
        user_id: str,
        days_back: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Generate comprehensive engagement insights for user.
        
        Args:
            user_id: User identifier
            days_back: Number of days to analyze
            
        Returns:
            Engagement insights and recommendations
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get recent deliveries
            recent_deliveries = [
                d for d in self.delivery_records.get(user_id, [])
                if d.sent_at and d.sent_at >= cutoff_date
            ]
            
            if not recent_deliveries:
                return {
                    "user_id": user_id,
                    "period_days": days_back,
                    "total_notifications": 0,
                    "engagement_summary": "No notifications sent in period",
                    "recommendations": ["Consider re-engaging user with relevant content"]
                }
            
            # Calculate metrics
            total_sent = len(recent_deliveries)
            total_delivered = len([d for d in recent_deliveries if d.status != NotificationStatus.FAILED])
            total_read = len([d for d in recent_deliveries if d.read_at])
            total_clicked = len([d for d in recent_deliveries if d.clicked_at])
            
            delivery_rate = total_delivered / total_sent if total_sent > 0 else 0
            read_rate = total_read / total_delivered if total_delivered > 0 else 0
            click_rate = total_clicked / total_delivered if total_delivered > 0 else 0
            
            # Analyze engagement patterns
            engagement_by_type = defaultdict(list)
            engagement_by_hour = defaultdict(list)
            engagement_by_channel = defaultdict(list)
            
            for delivery in recent_deliveries:
                if delivery.engagement_score:
                    engagement_by_type[delivery.notification_type.value].append(delivery.engagement_score)
                    if delivery.sent_at:
                        engagement_by_hour[delivery.sent_at.hour].append(delivery.engagement_score)
                    engagement_by_channel[delivery.delivery_channel.value].append(delivery.engagement_score)
            
            # Find optimal patterns
            best_type = max(engagement_by_type.items(), key=lambda x: statistics.mean(x[1]))[0] if engagement_by_type else None
            best_hour = max(engagement_by_hour.items(), key=lambda x: statistics.mean(x[1]))[0] if engagement_by_hour else None
            best_channel = max(engagement_by_channel.items(), key=lambda x: statistics.mean(x[1]))[0] if engagement_by_channel else None
            
            # Generate recommendations
            recommendations = self._generate_engagement_recommendations(
                user_id, recent_deliveries, delivery_rate, read_rate, click_rate
            )
            
            insights = {
                "user_id": user_id,
                "period_days": days_back,
                "total_notifications": total_sent,
                "metrics": {
                    "delivery_rate": delivery_rate,
                    "read_rate": read_rate,
                    "click_rate": click_rate,
                    "total_delivered": total_delivered,
                    "total_read": total_read,
                    "total_clicked": total_clicked
                },
                "optimal_patterns": {
                    "best_notification_type": best_type,
                    "best_hour": best_hour,
                    "best_channel": best_channel
                },
                "engagement_trends": {
                    "by_type": {k: statistics.mean(v) for k, v in engagement_by_type.items()},
                    "by_hour": {k: statistics.mean(v) for k, v in engagement_by_hour.items()},
                    "by_channel": {k: statistics.mean(v) for k, v in engagement_by_channel.items()}
                },
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating engagement insights: {e}")
            return None

    def optimize_notification_strategy(self, user_id: str) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations for user's notification strategy.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of optimization recommendations
        """
        try:
            recommendations = []
            
            # Analyze recent performance
            engagement_metrics = self.engagement_metrics.get(user_id)
            if not engagement_metrics:
                return []
            
            # Low engagement recommendations
            if engagement_metrics.read_rate < 0.3:
                recommendations.append(OptimizationRecommendation(
                    user_id=user_id,
                    recommendation_type="timing_optimization",
                    description="Low read rate suggests suboptimal timing",
                    expected_improvement=0.4,
                    confidence=0.8,
                    implementation_difficulty="easy",
                    suggested_actions=[
                        f"Send notifications during optimal hours: {engagement_metrics.optimal_times}",
                        "Test different days of the week",
                        "Reduce frequency to avoid notification fatigue"
                    ]
                ))
            
            # Channel optimization
            best_channel = self._find_best_performing_channel(user_id)
            if best_channel and engagement_metrics.delivery_rate < 0.9:
                recommendations.append(OptimizationRecommendation(
                    user_id=user_id,
                    recommendation_type="channel_optimization",
                    description="Switch to better performing delivery channel",
                    expected_improvement=0.3,
                    confidence=0.7,
                    implementation_difficulty="easy",
                    suggested_actions=[
                        f"Prioritize {best_channel} for critical notifications",
                        "Set up fallback delivery channels",
                        "Test multi-channel delivery for important messages"
                    ]
                ))
            
            # Frequency optimization
            if engagement_metrics.engagement_trend == "decreasing":
                recommendations.append(OptimizationRecommendation(
                    user_id=user_id,
                    recommendation_type="frequency_optimization",
                    description="Decreasing engagement suggests notification fatigue",
                    expected_improvement=0.5,
                    confidence=0.9,
                    implementation_difficulty="medium",
                    suggested_actions=[
                        "Reduce notification frequency by 30%",
                        "Focus on high-value notifications only",
                        "Implement smart batching for multiple updates"
                    ]
                ))
            
            # Content optimization
            if engagement_metrics.click_rate < 0.15:
                recommendations.append(OptimizationRecommendation(
                    user_id=user_id,
                    recommendation_type="content_optimization",
                    description="Low click rate indicates content needs improvement",
                    expected_improvement=0.6,
                    confidence=0.6,
                    implementation_difficulty="hard",
                    suggested_actions=[
                        "A/B test different message templates",
                        "Increase personalization level",
                        "Add clear call-to-action buttons",
                        "Use more engaging subject lines"
                    ]
                ))
            
            # Cache recommendations
            self.optimization_cache[user_id] = recommendations
            
            logger.info(f"Generated {len(recommendations)} optimization recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error optimizing notification strategy: {e}")
            return []

    def _get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get user preferences with defaults if not set."""
        if user_id in self.user_preferences:
            return self.user_preferences[user_id]
        
        # Create default preferences
        default_prefs = NotificationPreferences(
            user_id=user_id,
            enabled_types=set(self.default_preferences["enabled_types"]),
            quiet_hours=self.default_preferences["quiet_hours"],
            preferred_channels=self.default_preferences["preferred_channels"].copy(),
            frequency_limits=self.default_preferences["frequency_limits"].copy(),
            timezone="UTC"
        )
        
        self.user_preferences[user_id] = default_prefs
        return default_prefs

    def _select_optimal_channel(
        self,
        user_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority
    ) -> DeliveryChannel:
        """Select optimal delivery channel based on preferences and reliability."""
        preferences = self._get_user_preferences(user_id)
        
        # Check user preferences first
        if notification_type in preferences.preferred_channels:
            preferred_channels = preferences.preferred_channels[notification_type]
            if preferred_channels:
                return preferred_channels[0]  # Use most preferred
        
        # Fall back to priority-based selection
        if priority == NotificationPriority.URGENT:
            return DeliveryChannel.SMS  # Most reliable for urgent
        elif priority == NotificationPriority.HIGH:
            return DeliveryChannel.PUSH
        else:
            return DeliveryChannel.EMAIL

    def _optimize_delivery_time(
        self,
        user_id: str,
        notification_type: NotificationType,
        requested_time: datetime,
        preferences: NotificationPreferences
    ) -> datetime:
        """Optimize delivery time based on user behavior and preferences."""
        # Check quiet hours
        user_hour = requested_time.hour  # Simplified - should use user timezone
        quiet_start, quiet_end = preferences.quiet_hours
        
        if quiet_start <= quiet_end:
            # Normal quiet hours (e.g., 22:00 to 07:00)
            if quiet_start <= user_hour <= quiet_end:
                # Delay until after quiet hours
                next_day = requested_time.date() + timedelta(days=1)
                return datetime.combine(next_day, datetime.min.time()) + timedelta(hours=quiet_end + 1)
        else:
            # Quiet hours cross midnight (e.g., 22:00 to 07:00)
            if user_hour >= quiet_start or user_hour <= quiet_end:
                # Delay until after quiet hours
                if user_hour >= quiet_start:
                    # Today after quiet hours end
                    next_day = requested_time.date() + timedelta(days=1)
                    return datetime.combine(next_day, datetime.min.time()) + timedelta(hours=quiet_end + 1)
                else:
                    # Today after quiet hours end
                    return requested_time.replace(hour=quiet_end + 1, minute=0, second=0, microsecond=0)
        
        # Check if user has optimal times
        engagement_metrics = self.engagement_metrics.get(user_id)
        if engagement_metrics and engagement_metrics.optimal_times:
            optimal_hours = engagement_metrics.optimal_times
            current_hour = requested_time.hour
            
            # If not in optimal time, find nearest optimal time
            if current_hour not in optimal_hours:
                # Find nearest optimal hour
                nearest_hour = min(optimal_hours, key=lambda h: abs(h - current_hour))
                
                # Only adjust if within reasonable range (6 hours)
                if abs(nearest_hour - current_hour) <= 6:
                    optimized_time = requested_time.replace(hour=nearest_hour, minute=0, second=0, microsecond=0)
                    
                    # Make sure it's in the future
                    if optimized_time <= datetime.utcnow():
                        optimized_time += timedelta(days=1)
                    
                    return optimized_time
        
        return requested_time

    def _check_frequency_limits(
        self,
        user_id: str,
        notification_type: NotificationType,
        preferences: NotificationPreferences
    ) -> bool:
        """Check if notification is within frequency limits."""
        try:
            # Get recent deliveries
            recent_deliveries = self.delivery_records.get(user_id, [])
            
            # Check daily limit
            today = datetime.utcnow().date()
            today_count = len([
                d for d in recent_deliveries
                if d.sent_at and d.sent_at.date() == today and d.notification_type == notification_type
            ])
            
            daily_limit = preferences.frequency_limits.get("daily", 10)
            if today_count >= daily_limit:
                return False
            
            # Check weekly limit
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_count = len([
                d for d in recent_deliveries
                if d.sent_at and d.sent_at >= week_ago and d.notification_type == notification_type
            ])
            
            weekly_limit = preferences.frequency_limits.get("weekly", 20)
            if week_count >= weekly_limit:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking frequency limits: {e}")
            return True  # Allow if check fails

    def _deliver_via_channel(
        self,
        schedule: NotificationSchedule,
        delivery: NotificationDelivery
    ) -> Tuple[bool, Optional[str]]:
        """Deliver notification via specified channel."""
        try:
            channel = schedule.delivery_channel
            
            if channel == DeliveryChannel.SMS:
                return self._deliver_via_sms(schedule, delivery)
            elif channel == DeliveryChannel.EMAIL:
                return self._deliver_via_email(schedule, delivery)
            elif channel == DeliveryChannel.PUSH:
                return self._deliver_via_push(schedule, delivery)
            elif channel == DeliveryChannel.IN_APP:
                return self._deliver_via_in_app(schedule, delivery)
            elif channel == DeliveryChannel.WEBHOOK:
                return self._deliver_via_webhook(schedule, delivery)
            else:
                return False, f"Unsupported delivery channel: {channel}"
                
        except Exception as e:
            logger.error(f"Error delivering via channel: {e}")
            return False, str(e)

    def _deliver_via_sms(self, schedule: NotificationSchedule, delivery: NotificationDelivery) -> Tuple[bool, Optional[str]]:
        """Deliver notification via SMS."""
        # Integration with SMS service
        # For now, simulate delivery
        logger.info(f"SMS delivery simulated for {schedule.user_id}: {schedule.title}")
        return True, None

    def _deliver_via_email(self, schedule: NotificationSchedule, delivery: NotificationDelivery) -> Tuple[bool, Optional[str]]:
        """Deliver notification via email."""
        # Integration with email service
        logger.info(f"Email delivery simulated for {schedule.user_id}: {schedule.title}")
        return True, None

    def _deliver_via_push(self, schedule: NotificationSchedule, delivery: NotificationDelivery) -> Tuple[bool, Optional[str]]:
        """Deliver notification via push notification."""
        # Integration with push notification service
        logger.info(f"Push delivery simulated for {schedule.user_id}: {schedule.title}")
        return True, None

    def _deliver_via_in_app(self, schedule: NotificationSchedule, delivery: NotificationDelivery) -> Tuple[bool, Optional[str]]:
        """Deliver notification via in-app messaging."""
        # Integration with in-app messaging
        logger.info(f"In-app delivery simulated for {schedule.user_id}: {schedule.title}")
        return True, None

    def _deliver_via_webhook(self, schedule: NotificationSchedule, delivery: NotificationDelivery) -> Tuple[bool, Optional[str]]:
        """Deliver notification via webhook."""
        # Integration with webhook service
        logger.info(f"Webhook delivery simulated for {schedule.user_id}: {schedule.title}")
        return True, None

    def _try_fallback_delivery(self, schedule: NotificationSchedule, delivery: NotificationDelivery) -> bool:
        """Try fallback delivery method if primary channel fails."""
        # Define fallback chain
        fallback_chain = {
            DeliveryChannel.PUSH: DeliveryChannel.SMS,
            DeliveryChannel.EMAIL: DeliveryChannel.SMS,
            DeliveryChannel.IN_APP: DeliveryChannel.PUSH,
            DeliveryChannel.WEBHOOK: DeliveryChannel.EMAIL
        }
        
        current_channel = schedule.delivery_channel
        fallback_channel = fallback_chain.get(current_channel)
        
        if fallback_channel:
            logger.info(f"Trying fallback delivery: {current_channel.value} -> {fallback_channel.value}")
            schedule.delivery_channel = fallback_channel
            success, _ = self._deliver_via_channel(schedule, delivery)
            if success:
                delivery.metadata["fallback_used"] = fallback_channel.value
                return True
        
        return False

    def _calculate_engagement_score(self, delivery: NotificationDelivery) -> float:
        """Calculate engagement score for a delivery."""
        score = 0.0
        
        # Base score for delivery
        if delivery.status != NotificationStatus.FAILED:
            score += 0.3
        
        # Read engagement
        if delivery.read_at:
            score += 0.4
            
            # Time to read bonus (faster = more engaging)
            if delivery.sent_at and delivery.read_at:
                time_to_read = (delivery.read_at - delivery.sent_at).total_seconds()
                if time_to_read < 300:  # Read within 5 minutes
                    score += 0.2
                elif time_to_read < 3600:  # Read within 1 hour
                    score += 0.1
        
        # Click engagement
        if delivery.clicked_at:
            score += 0.3
        
        return min(1.0, score)

    def _update_engagement_metrics(self, user_id: str) -> None:
        """Update engagement metrics for user."""
        try:
            deliveries = self.delivery_records.get(user_id, [])
            if not deliveries:
                return
            
            # Calculate metrics from last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            recent_deliveries = [d for d in deliveries if d.sent_at and d.sent_at >= cutoff_date]
            
            if not recent_deliveries:
                return
            
            # Calculate rates
            total_sent = len(recent_deliveries)
            total_delivered = len([d for d in recent_deliveries if d.status != NotificationStatus.FAILED])
            total_read = len([d for d in recent_deliveries if d.read_at])
            total_clicked = len([d for d in recent_deliveries if d.clicked_at])
            
            delivery_rate = total_delivered / total_sent if total_sent > 0 else 0
            read_rate = total_read / total_delivered if total_delivered > 0 else 0
            click_rate = total_clicked / total_delivered if total_delivered > 0 else 0
            
            # Find optimal times
            hour_engagement = defaultdict(list)
            for delivery in recent_deliveries:
                if delivery.sent_at and delivery.engagement_score:
                    hour_engagement[delivery.sent_at.hour].append(delivery.engagement_score)
            
            optimal_times = []
            for hour, scores in hour_engagement.items():
                avg_score = statistics.mean(scores)
                if avg_score > 0.6:  # Good engagement threshold
                    optimal_times.append(hour)
            
            # Determine engagement trend
            if len(recent_deliveries) >= 10:
                first_half = recent_deliveries[:len(recent_deliveries)//2]
                second_half = recent_deliveries[len(recent_deliveries)//2:]
                
                first_half_avg = statistics.mean([d.engagement_score for d in first_half if d.engagement_score])
                second_half_avg = statistics.mean([d.engagement_score for d in second_half if d.engagement_score])
                
                if second_half_avg > first_half_avg * 1.1:
                    trend = "increasing"
                elif second_half_avg < first_half_avg * 0.9:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "stable"
            
            # Get last engagement time
            last_engagement = max([d.clicked_at or d.read_at or d.sent_at for d in recent_deliveries])
            
            # Update metrics
            metrics = EngagementMetrics(
                user_id=user_id,
                total_sent=total_sent,
                total_delivered=total_delivered,
                total_read=total_read,
                total_clicked=total_clicked,
                delivery_rate=delivery_rate,
                read_rate=read_rate,
                click_rate=click_rate,
                optimal_times=optimal_times,
                preferred_frequency=total_sent // 4,  # Weekly average
                engagement_trend=trend,
                last_engagement=last_engagement
            )
            
            self.engagement_metrics[user_id] = metrics
            
        except Exception as e:
            logger.error(f"Error updating engagement metrics: {e}")

    def _trigger_optimization_if_needed(self, user_id: str) -> None:
        """Trigger optimization analysis if metrics indicate need."""
        metrics = self.engagement_metrics.get(user_id)
        if not metrics:
            return
        
        # Trigger optimization if performance is declining
        if (metrics.read_rate < 0.3 or 
            metrics.engagement_trend == "decreasing" or
            metrics.delivery_rate < 0.8):
            
            logger.info(f"Triggering optimization for user {user_id} due to poor metrics")
            self.optimize_notification_strategy(user_id)

    def _generate_engagement_recommendations(
        self,
        user_id: str,
        deliveries: List[NotificationDelivery],
        delivery_rate: float,
        read_rate: float,
        click_rate: float
    ) -> List[str]:
        """Generate engagement improvement recommendations."""
        recommendations = []
        
        if delivery_rate < 0.8:
            recommendations.append("Improve delivery rate by using more reliable channels")
        
        if read_rate < 0.4:
            recommendations.append("Optimize send times to increase read rates")
            recommendations.append("Improve subject lines and preview text")
        
        if click_rate < 0.15:
            recommendations.append("Add clear call-to-action elements")
            recommendations.append("Increase content personalization")
        
        # Analyze failure patterns
        failed_deliveries = [d for d in deliveries if d.status == NotificationStatus.FAILED]
        if len(failed_deliveries) > len(deliveries) * 0.2:
            recommendations.append("Set up fallback delivery channels to reduce failures")
        
        return recommendations

    def _find_best_performing_channel(self, user_id: str) -> Optional[str]:
        """Find the best performing delivery channel for user."""
        deliveries = self.delivery_records.get(user_id, [])
        if not deliveries:
            return None
        
        channel_performance = defaultdict(list)
        for delivery in deliveries:
            if delivery.engagement_score:
                channel_performance[delivery.delivery_channel.value].append(delivery.engagement_score)
        
        if not channel_performance:
            return None
        
        # Find channel with highest average engagement
        best_channel = max(
            channel_performance.items(),
            key=lambda x: statistics.mean(x[1])
        )[0]
        
        return best_channel

    def _initialize_default_preferences(self) -> Dict[str, Any]:
        """Initialize default notification preferences."""
        return {
            "enabled_types": [
                NotificationType.MEAL_REMINDER,
                NotificationType.GOAL_UPDATE,
                NotificationType.WEEKLY_SUMMARY,
                NotificationType.ACHIEVEMENT
            ],
            "quiet_hours": (22, 7),  # 10 PM to 7 AM
            "preferred_channels": {
                NotificationType.MEAL_REMINDER: [DeliveryChannel.PUSH, DeliveryChannel.SMS],
                NotificationType.GOAL_UPDATE: [DeliveryChannel.PUSH, DeliveryChannel.EMAIL],
                NotificationType.WEEKLY_SUMMARY: [DeliveryChannel.EMAIL],
                NotificationType.ACHIEVEMENT: [DeliveryChannel.PUSH, DeliveryChannel.SMS],
                NotificationType.SYSTEM_ALERT: [DeliveryChannel.SMS, DeliveryChannel.EMAIL]
            },
            "frequency_limits": {
                "daily": 5,
                "weekly": 15
            }
        }

    def _initialize_channel_reliability(self) -> Dict[DeliveryChannel, float]:
        """Initialize delivery channel reliability scores."""
        return {
            DeliveryChannel.SMS: 0.95,
            DeliveryChannel.PUSH: 0.85,
            DeliveryChannel.EMAIL: 0.90,
            DeliveryChannel.IN_APP: 0.80,
            DeliveryChannel.WEBHOOK: 0.75
        }
