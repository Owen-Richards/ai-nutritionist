"""
Business Metrics Tracker

Tracks business-specific metrics including user engagement, feature usage,
conversion rates, and revenue metrics with CloudWatch integration.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class UserEngagementMetrics:
    """User engagement tracking metrics"""
    user_id: str
    timestamp: datetime
    session_id: str
    action: str
    feature: str
    duration_seconds: float
    success: bool
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureUsageMetrics:
    """Feature usage tracking metrics"""
    feature_name: str
    timestamp: datetime
    user_id: str
    usage_count: int
    session_duration: float
    completion_rate: float
    user_satisfaction: Optional[float] = None


@dataclass
class ConversionMetrics:
    """Conversion tracking metrics"""
    funnel_stage: str
    timestamp: datetime
    user_id: str
    conversion_event: str
    conversion_value: float
    source: str
    campaign: Optional[str] = None


@dataclass
class RevenueMetrics:
    """Revenue tracking metrics"""
    timestamp: datetime
    user_id: str
    revenue_amount: float
    currency: str
    subscription_type: str
    payment_method: str
    transaction_id: str
    is_recurring: bool


class BusinessMetricsTracker:
    """
    Comprehensive business metrics tracking with CloudWatch integration
    """
    
    def __init__(
        self,
        namespace: str = "AINutritionist/Business",
        region: str = "us-east-1"
    ):
        self.namespace = namespace
        self.region = region
        
        # AWS clients
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}")
            self.cloudwatch = None
        
        # Metrics storage
        self.engagement_metrics: List[UserEngagementMetrics] = []
        self.feature_metrics: List[FeatureUsageMetrics] = []
        self.conversion_metrics: List[ConversionMetrics] = []
        self.revenue_metrics: List[RevenueMetrics] = []
        
        # Real-time counters
        self.active_users: Set[str] = set()
        self.daily_active_users: Set[str] = set()
        self.feature_usage_counts: Dict[str, int] = defaultdict(int)
        self.conversion_counts: Dict[str, int] = defaultdict(int)
        self.daily_revenue: float = 0.0
        
        # User sessions
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.flush_interval = 300  # 5 minutes
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background metric processing tasks"""
        asyncio.create_task(self._periodic_flush())
        asyncio.create_task(self._cleanup_old_data())
    
    async def track_user_engagement(
        self,
        user_id: str,
        action: str,
        feature: str,
        duration_seconds: float = 0.0,
        success: bool = True,
        context: Optional[Dict[str, Any]] = None
    ):
        """Track user engagement event"""
        session_id = self._get_or_create_session(user_id)
        
        metrics = UserEngagementMetrics(
            user_id=user_id,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            action=action,
            feature=feature,
            duration_seconds=duration_seconds,
            success=success,
            context=context or {}
        )
        
        self.engagement_metrics.append(metrics)
        
        # Update real-time counters
        self.active_users.add(user_id)
        self.daily_active_users.add(user_id)
        
        # Update session
        self._update_user_session(user_id, action, feature, duration_seconds)
        
        # Send to CloudWatch
        await self._send_engagement_metrics(metrics)
    
    async def track_feature_usage(
        self,
        user_id: str,
        feature_name: str,
        usage_count: int = 1,
        session_duration: float = 0.0,
        completion_rate: float = 1.0,
        user_satisfaction: Optional[float] = None
    ):
        """Track feature usage metrics"""
        metrics = FeatureUsageMetrics(
            feature_name=feature_name,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            usage_count=usage_count,
            session_duration=session_duration,
            completion_rate=completion_rate,
            user_satisfaction=user_satisfaction
        )
        
        self.feature_metrics.append(metrics)
        self.feature_usage_counts[feature_name] += usage_count
        
        # Send to CloudWatch
        await self._send_feature_metrics(metrics)
    
    async def track_conversion_event(
        self,
        user_id: str,
        funnel_stage: str,
        conversion_event: str,
        conversion_value: float = 1.0,
        source: str = "direct",
        campaign: Optional[str] = None
    ):
        """Track conversion funnel events"""
        metrics = ConversionMetrics(
            funnel_stage=funnel_stage,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            conversion_event=conversion_event,
            conversion_value=conversion_value,
            source=source,
            campaign=campaign
        )
        
        self.conversion_metrics.append(metrics)
        self.conversion_counts[f"{funnel_stage}:{conversion_event}"] += 1
        
        # Send to CloudWatch
        await self._send_conversion_metrics(metrics)
    
    async def track_revenue_event(
        self,
        user_id: str,
        revenue_amount: float,
        currency: str = "USD",
        subscription_type: str = "premium",
        payment_method: str = "credit_card",
        transaction_id: str = "",
        is_recurring: bool = True
    ):
        """Track revenue events"""
        metrics = RevenueMetrics(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            revenue_amount=revenue_amount,
            currency=currency,
            subscription_type=subscription_type,
            payment_method=payment_method,
            transaction_id=transaction_id or f"txn_{int(datetime.utcnow().timestamp())}",
            is_recurring=is_recurring
        )
        
        self.revenue_metrics.append(metrics)
        self.daily_revenue += revenue_amount
        
        # Send to CloudWatch
        await self._send_revenue_metrics(metrics)
    
    def _get_or_create_session(self, user_id: str) -> str:
        """Get or create user session"""
        current_time = datetime.utcnow()
        
        if user_id not in self.user_sessions:
            session_id = f"{user_id}_{int(current_time.timestamp())}"
            self.user_sessions[user_id] = {
                'session_id': session_id,
                'start_time': current_time,
                'last_activity': current_time,
                'action_count': 0,
                'features_used': set(),
                'total_duration': 0.0
            }
        else:
            # Check if session is still active (within 30 minutes)
            last_activity = self.user_sessions[user_id]['last_activity']
            if (current_time - last_activity).total_seconds() > 1800:  # 30 minutes
                session_id = f"{user_id}_{int(current_time.timestamp())}"
                self.user_sessions[user_id] = {
                    'session_id': session_id,
                    'start_time': current_time,
                    'last_activity': current_time,
                    'action_count': 0,
                    'features_used': set(),
                    'total_duration': 0.0
                }
        
        return self.user_sessions[user_id]['session_id']
    
    def _update_user_session(self, user_id: str, action: str, feature: str, duration: float):
        """Update user session data"""
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            session['last_activity'] = datetime.utcnow()
            session['action_count'] += 1
            session['features_used'].add(feature)
            session['total_duration'] += duration
    
    async def _send_engagement_metrics(self, metrics: UserEngagementMetrics):
        """Send engagement metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'UserEngagement',
                    'Dimensions': [
                        {'Name': 'Action', 'Value': metrics.action},
                        {'Name': 'Feature', 'Value': metrics.feature}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'SessionDuration',
                    'Dimensions': [
                        {'Name': 'Feature', 'Value': metrics.feature}
                    ],
                    'Value': metrics.duration_seconds,
                    'Unit': 'Seconds',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'EngagementSuccess',
                    'Dimensions': [
                        {'Name': 'Action', 'Value': metrics.action},
                        {'Name': 'Feature', 'Value': metrics.feature}
                    ],
                    'Value': 1 if metrics.success else 0,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace=f"{self.namespace}/Engagement",
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send engagement metrics to CloudWatch: {e}")
    
    async def _send_feature_metrics(self, metrics: FeatureUsageMetrics):
        """Send feature usage metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'FeatureUsage',
                    'Dimensions': [
                        {'Name': 'FeatureName', 'Value': metrics.feature_name}
                    ],
                    'Value': metrics.usage_count,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'FeatureSessionDuration',
                    'Dimensions': [
                        {'Name': 'FeatureName', 'Value': metrics.feature_name}
                    ],
                    'Value': metrics.session_duration,
                    'Unit': 'Seconds',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'FeatureCompletionRate',
                    'Dimensions': [
                        {'Name': 'FeatureName', 'Value': metrics.feature_name}
                    ],
                    'Value': metrics.completion_rate * 100,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            if metrics.user_satisfaction is not None:
                metric_data.append({
                    'MetricName': 'UserSatisfaction',
                    'Dimensions': [
                        {'Name': 'FeatureName', 'Value': metrics.feature_name}
                    ],
                    'Value': metrics.user_satisfaction,
                    'Unit': 'None',
                    'Timestamp': metrics.timestamp
                })
            
            self.cloudwatch.put_metric_data(
                Namespace=f"{self.namespace}/Features",
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send feature metrics to CloudWatch: {e}")
    
    async def _send_conversion_metrics(self, metrics: ConversionMetrics):
        """Send conversion metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'ConversionEvent',
                    'Dimensions': [
                        {'Name': 'FunnelStage', 'Value': metrics.funnel_stage},
                        {'Name': 'ConversionType', 'Value': metrics.conversion_event},
                        {'Name': 'Source', 'Value': metrics.source}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'ConversionValue',
                    'Dimensions': [
                        {'Name': 'FunnelStage', 'Value': metrics.funnel_stage},
                        {'Name': 'ConversionType', 'Value': metrics.conversion_event}
                    ],
                    'Value': metrics.conversion_value,
                    'Unit': 'None',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            if metrics.campaign:
                metric_data.append({
                    'MetricName': 'ConversionByCampaign',
                    'Dimensions': [
                        {'Name': 'Campaign', 'Value': metrics.campaign},
                        {'Name': 'ConversionType', 'Value': metrics.conversion_event}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                })
            
            self.cloudwatch.put_metric_data(
                Namespace=f"{self.namespace}/Conversions",
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send conversion metrics to CloudWatch: {e}")
    
    async def _send_revenue_metrics(self, metrics: RevenueMetrics):
        """Send revenue metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'Revenue',
                    'Dimensions': [
                        {'Name': 'SubscriptionType', 'Value': metrics.subscription_type},
                        {'Name': 'PaymentMethod', 'Value': metrics.payment_method},
                        {'Name': 'Currency', 'Value': metrics.currency}
                    ],
                    'Value': metrics.revenue_amount,
                    'Unit': 'None',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'RevenueTransactions',
                    'Dimensions': [
                        {'Name': 'SubscriptionType', 'Value': metrics.subscription_type},
                        {'Name': 'RecurringFlag', 'Value': str(metrics.is_recurring)}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace=f"{self.namespace}/Revenue",
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send revenue metrics to CloudWatch: {e}")
    
    async def _periodic_flush(self):
        """Periodically flush aggregated business metrics"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_aggregated_business_metrics()
            except Exception as e:
                logger.error(f"Error in business metrics periodic flush: {e}")
    
    async def _flush_aggregated_business_metrics(self):
        """Flush aggregated business metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            current_time = datetime.utcnow()
            
            # Calculate time-based metrics
            active_user_count = len(self.active_users)
            daily_active_user_count = len(self.daily_active_users)
            
            # Feature usage aggregation
            top_features = sorted(
                self.feature_usage_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Session metrics
            active_sessions = len(self.user_sessions)
            avg_session_duration = 0.0
            if self.user_sessions:
                total_duration = sum(
                    session['total_duration'] 
                    for session in self.user_sessions.values()
                )
                avg_session_duration = total_duration / len(self.user_sessions)
            
            metric_data = [
                {
                    'MetricName': 'ActiveUsers',
                    'Value': active_user_count,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'DailyActiveUsers',
                    'Value': daily_active_user_count,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'ActiveSessions',
                    'Value': active_sessions,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'AverageSessionDuration',
                    'Value': avg_session_duration,
                    'Unit': 'Seconds',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'DailyRevenue',
                    'Value': self.daily_revenue,
                    'Unit': 'None',
                    'Timestamp': current_time
                }
            ]
            
            # Add top features usage
            for feature, count in top_features:
                metric_data.append({
                    'MetricName': 'TopFeatureUsage',
                    'Dimensions': [
                        {'Name': 'FeatureName', 'Value': feature}
                    ],
                    'Value': count,
                    'Unit': 'Count',
                    'Timestamp': current_time
                })
            
            self.cloudwatch.put_metric_data(
                Namespace=f"{self.namespace}/Aggregated",
                MetricData=metric_data
            )
            
            # Reset active users for next period
            self.active_users.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush aggregated business metrics: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old metrics data to prevent memory leaks"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Clean up old metrics
                self.engagement_metrics = [
                    m for m in self.engagement_metrics 
                    if m.timestamp > cutoff_time
                ]
                self.feature_metrics = [
                    m for m in self.feature_metrics 
                    if m.timestamp > cutoff_time
                ]
                self.conversion_metrics = [
                    m for m in self.conversion_metrics 
                    if m.timestamp > cutoff_time
                ]
                self.revenue_metrics = [
                    m for m in self.revenue_metrics 
                    if m.timestamp > cutoff_time
                ]
                
                # Clean up old sessions
                current_time = datetime.utcnow()
                inactive_users = []
                for user_id, session in self.user_sessions.items():
                    if (current_time - session['last_activity']).total_seconds() > 7200:  # 2 hours
                        inactive_users.append(user_id)
                
                for user_id in inactive_users:
                    del self.user_sessions[user_id]
                
                logger.debug(f"Cleaned up old metrics data and {len(inactive_users)} inactive sessions")
                
            except Exception as e:
                logger.error(f"Error in cleanup old data: {e}")
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Get business metrics summary"""
        current_time = datetime.utcnow()
        
        # Calculate metrics for the last hour
        hour_ago = current_time - timedelta(hours=1)
        
        recent_engagement = [
            m for m in self.engagement_metrics 
            if m.timestamp > hour_ago
        ]
        recent_conversions = [
            m for m in self.conversion_metrics 
            if m.timestamp > hour_ago
        ]
        recent_revenue = [
            m for m in self.revenue_metrics 
            if m.timestamp > hour_ago
        ]
        
        # Calculate engagement rate
        successful_engagements = len([m for m in recent_engagement if m.success])
        engagement_rate = (successful_engagements / len(recent_engagement) * 100) if recent_engagement else 0
        
        # Calculate revenue
        hourly_revenue = sum(m.revenue_amount for m in recent_revenue)
        
        # Most used features
        feature_counts = defaultdict(int)
        for m in recent_engagement:
            feature_counts[m.feature] += 1
        
        top_features = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'timestamp': current_time.isoformat(),
            'active_users_current': len(self.active_users),
            'daily_active_users': len(self.daily_active_users),
            'active_sessions': len(self.user_sessions),
            'hourly_engagement_events': len(recent_engagement),
            'engagement_success_rate_percent': engagement_rate,
            'hourly_conversions': len(recent_conversions),
            'hourly_revenue': hourly_revenue,
            'daily_revenue_total': self.daily_revenue,
            'top_features_last_hour': dict(top_features),
            'average_session_duration_seconds': (
                sum(s['total_duration'] for s in self.user_sessions.values()) / 
                len(self.user_sessions)
            ) if self.user_sessions else 0
        }


# Global business metrics tracker
_business_tracker: Optional[BusinessMetricsTracker] = None


def get_business_tracker() -> BusinessMetricsTracker:
    """Get or create global business metrics tracker"""
    global _business_tracker
    if _business_tracker is None:
        _business_tracker = BusinessMetricsTracker()
    return _business_tracker


def setup_business_tracking(**kwargs) -> BusinessMetricsTracker:
    """Setup business metrics tracking"""
    global _business_tracker
    _business_tracker = BusinessMetricsTracker(**kwargs)
    return _business_tracker
