"""
Alert Manager

Manages CloudWatch alarms and alert policies for comprehensive monitoring
with intelligent alerting, escalation policies, and notification management.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertState(Enum):
    """Alert states"""
    OK = "OK"
    ALARM = "ALARM"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    description: str
    metric_name: str
    namespace: str
    dimensions: List[Dict[str, str]]
    comparison_operator: str
    threshold: float
    evaluation_periods: int
    period: int
    statistic: str
    severity: AlertSeverity
    notification_channels: List[str]
    treat_missing_data: str = "notBreaching"
    datapoints_to_alarm: Optional[int] = None


@dataclass
class AlertNotification:
    """Alert notification data"""
    alert_name: str
    severity: AlertSeverity
    state: AlertState
    timestamp: datetime
    message: str
    metric_data: Dict[str, Any]
    runbook_url: Optional[str] = None


class AlertManager:
    """
    Comprehensive alert management with CloudWatch alarms and intelligent notifications
    """
    
    def __init__(
        self,
        service_name: str = "ai-nutritionist",
        region: str = "us-east-1",
        sns_topic_arn: Optional[str] = None
    ):
        self.service_name = service_name
        self.region = region
        self.sns_topic_arn = sns_topic_arn
        
        # AWS clients
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=region)
            self.sns = boto3.client('sns', region_name=region)
        except Exception as e:
            logger.warning(f"Failed to initialize AWS clients: {e}")
            self.cloudwatch = None
            self.sns = None
        
        # Alert configurations
        self.alert_rules = self._get_default_alert_rules()
        self.active_alerts: Dict[str, AlertNotification] = {}
        self.alert_history: List[AlertNotification] = []
        
        # Escalation policies
        self.escalation_policies = self._get_escalation_policies()
        
        # Notification channels
        self.notification_channels = {
            'email': self._send_email_notification,
            'slack': self._send_slack_notification,
            'pagerduty': self._send_pagerduty_notification,
            'sms': self._send_sms_notification
        }
        
        # Alert suppression
        self.suppression_rules: Dict[str, datetime] = {}
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background alert processing tasks"""
        asyncio.create_task(self._monitor_alert_states())
        asyncio.create_task(self._process_escalations())
        asyncio.create_task(self._cleanup_old_alerts())
    
    async def setup_all_alerts(self) -> Dict[str, str]:
        """Setup all alert rules"""
        created_alarms = {}
        
        for rule in self.alert_rules:
            try:
                alarm_arn = await self._create_cloudwatch_alarm(rule)
                created_alarms[rule.name] = alarm_arn
                logger.info(f"Created alarm: {rule.name}")
            except Exception as e:
                logger.error(f"Failed to create alarm {rule.name}: {e}")
                created_alarms[rule.name] = f"ERROR: {str(e)}"
        
        return created_alarms
    
    async def create_alert_rule(self, rule: AlertRule) -> str:
        """Create a specific alert rule"""
        return await self._create_cloudwatch_alarm(rule)
    
    async def _create_cloudwatch_alarm(self, rule: AlertRule) -> str:
        """Create a CloudWatch alarm from an alert rule"""
        if not self.cloudwatch:
            raise Exception("CloudWatch client not available")
        
        alarm_name = f"{self.service_name}-{rule.name}"
        
        # Prepare alarm actions
        alarm_actions = []
        ok_actions = []
        
        if self.sns_topic_arn:
            alarm_actions.append(self.sns_topic_arn)
            ok_actions.append(self.sns_topic_arn)
        
        try:
            response = self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                AlarmDescription=rule.description,
                ActionsEnabled=True,
                AlarmActions=alarm_actions,
                OKActions=ok_actions,
                MetricName=rule.metric_name,
                Namespace=rule.namespace,
                Statistic=rule.statistic,
                Dimensions=rule.dimensions,
                Period=rule.period,
                EvaluationPeriods=rule.evaluation_periods,
                DatapointsToAlarm=rule.datapoints_to_alarm or rule.evaluation_periods,
                Threshold=rule.threshold,
                ComparisonOperator=rule.comparison_operator,
                TreatMissingData=rule.treat_missing_data,
                Tags=[
                    {'Key': 'Service', 'Value': self.service_name},
                    {'Key': 'Severity', 'Value': rule.severity.value},
                    {'Key': 'Environment', 'Value': 'production'}
                ]
            )
            
            return f"arn:aws:cloudwatch:{self.region}:*:alarm:{alarm_name}"
            
        except ClientError as e:
            raise Exception(f"Failed to create CloudWatch alarm: {e}")
    
    def _get_default_alert_rules(self) -> List[AlertRule]:
        """Get default alert rules for the service"""
        return [
            # Performance Alerts
            AlertRule(
                name="high-response-time",
                description="Average response time is too high",
                metric_name="AverageResponseTime",
                namespace="AINutritionist/Performance/Aggregated",
                dimensions=[{'Name': 'Service', 'Value': self.service_name}],
                comparison_operator="GreaterThanThreshold",
                threshold=5000.0,  # 5 seconds
                evaluation_periods=2,
                period=300,
                statistic="Average",
                severity=AlertSeverity.HIGH,
                notification_channels=['email', 'slack']
            ),
            
            AlertRule(
                name="high-error-rate",
                description="Error rate is above acceptable threshold",
                metric_name="ErrorRatePercent",
                namespace="AINutritionist/Performance/Aggregated",
                dimensions=[{'Name': 'Service', 'Value': self.service_name}],
                comparison_operator="GreaterThanThreshold",
                threshold=5.0,  # 5%
                evaluation_periods=2,
                period=300,
                statistic="Average",
                severity=AlertSeverity.CRITICAL,
                notification_channels=['email', 'slack', 'pagerduty']
            ),
            
            AlertRule(
                name="low-throughput",
                description="Request throughput is unusually low",
                metric_name="RequestsPerSecond",
                namespace="AINutritionist/Performance",
                dimensions=[{'Name': 'Service', 'Value': self.service_name}],
                comparison_operator="LessThanThreshold",
                threshold=1.0,  # 1 RPS
                evaluation_periods=3,
                period=300,
                statistic="Average",
                severity=AlertSeverity.MEDIUM,
                notification_channels=['email']
            ),
            
            # Infrastructure Alerts
            AlertRule(
                name="high-cpu-utilization",
                description="CPU utilization is critically high",
                metric_name="CPUUtilization",
                namespace="AINutritionist/Infrastructure",
                dimensions=[{'Name': 'Service', 'Value': self.service_name}],
                comparison_operator="GreaterThanThreshold",
                threshold=80.0,  # 80%
                evaluation_periods=2,
                period=300,
                statistic="Average",
                severity=AlertSeverity.HIGH,
                notification_channels=['email', 'slack']
            ),
            
            AlertRule(
                name="high-memory-utilization",
                description="Memory utilization is critically high",
                metric_name="MemoryUtilization",
                namespace="AINutritionist/Infrastructure",
                dimensions=[{'Name': 'Service', 'Value': self.service_name}],
                comparison_operator="GreaterThanThreshold",
                threshold=85.0,  # 85%
                evaluation_periods=2,
                period=300,
                statistic="Average",
                severity=AlertSeverity.HIGH,
                notification_channels=['email', 'slack']
            ),
            
            AlertRule(
                name="disk-space-low",
                description="Disk utilization is critically high",
                metric_name="DiskUtilization",
                namespace="AINutritionist/Infrastructure",
                dimensions=[{'Name': 'Service', 'Value': self.service_name}],
                comparison_operator="GreaterThanThreshold",
                threshold=90.0,  # 90%
                evaluation_periods=1,
                period=300,
                statistic="Average",
                severity=AlertSeverity.CRITICAL,
                notification_channels=['email', 'slack', 'pagerduty']
            ),
            
            # Business Alerts
            AlertRule(
                name="revenue-drop",
                description="Daily revenue has dropped significantly",
                metric_name="DailyRevenue",
                namespace="AINutritionist/Business/Aggregated",
                dimensions=[],
                comparison_operator="LessThanThreshold",
                threshold=100.0,  # $100
                evaluation_periods=1,
                period=86400,  # 1 day
                statistic="Sum",
                severity=AlertSeverity.HIGH,
                notification_channels=['email', 'slack']
            ),
            
            AlertRule(
                name="user-engagement-low",
                description="Daily active users below threshold",
                metric_name="DailyActiveUsers",
                namespace="AINutritionist/Business/Aggregated",
                dimensions=[],
                comparison_operator="LessThanThreshold",
                threshold=10.0,  # 10 users
                evaluation_periods=1,
                period=86400,  # 1 day
                statistic="Maximum",
                severity=AlertSeverity.MEDIUM,
                notification_channels=['email']
            ),
            
            # AWS Service Alerts
            AlertRule(
                name="lambda-high-duration",
                description="Lambda function duration is high",
                metric_name="Duration",
                namespace="AWS/Lambda",
                dimensions=[{'Name': 'FunctionName', 'Value': f'{self.service_name}-nutrition-handler'}],
                comparison_operator="GreaterThanThreshold",
                threshold=25000.0,  # 25 seconds
                evaluation_periods=2,
                period=300,
                statistic="Average",
                severity=AlertSeverity.HIGH,
                notification_channels=['email', 'slack']
            ),
            
            AlertRule(
                name="dynamodb-throttles",
                description="DynamoDB table is being throttled",
                metric_name="ThrottledRequests",
                namespace="AWS/DynamoDB",
                dimensions=[{'Name': 'TableName', 'Value': f'{self.service_name}-user-data'}],
                comparison_operator="GreaterThanThreshold",
                threshold=0,
                evaluation_periods=1,
                period=300,
                statistic="Sum",
                severity=AlertSeverity.CRITICAL,
                notification_channels=['email', 'slack', 'pagerduty']
            ),
            
            AlertRule(
                name="api-gateway-5xx-errors",
                description="API Gateway is returning 5XX errors",
                metric_name="5XXError",
                namespace="AWS/ApiGateway",
                dimensions=[{'Name': 'ApiName', 'Value': f'{self.service_name}-api'}],
                comparison_operator="GreaterThanThreshold",
                threshold=5,
                evaluation_periods=2,
                period=300,
                statistic="Sum",
                severity=AlertSeverity.CRITICAL,
                notification_channels=['email', 'slack', 'pagerduty']
            )
        ]
    
    def _get_escalation_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get escalation policies for different alert severities"""
        return {
            AlertSeverity.CRITICAL.value: {
                'initial_notification': ['email', 'slack', 'pagerduty'],
                'escalation_time_minutes': 15,
                'escalation_channels': ['sms', 'pagerduty'],
                'max_escalations': 3
            },
            AlertSeverity.HIGH.value: {
                'initial_notification': ['email', 'slack'],
                'escalation_time_minutes': 30,
                'escalation_channels': ['sms'],
                'max_escalations': 2
            },
            AlertSeverity.MEDIUM.value: {
                'initial_notification': ['email'],
                'escalation_time_minutes': 60,
                'escalation_channels': ['slack'],
                'max_escalations': 1
            },
            AlertSeverity.LOW.value: {
                'initial_notification': ['email'],
                'escalation_time_minutes': 120,
                'escalation_channels': [],
                'max_escalations': 0
            },
            AlertSeverity.INFO.value: {
                'initial_notification': ['email'],
                'escalation_time_minutes': 0,
                'escalation_channels': [],
                'max_escalations': 0
            }
        }
    
    async def _monitor_alert_states(self):
        """Monitor CloudWatch alarm states"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._check_alarm_states()
            except Exception as e:
                logger.error(f"Error monitoring alert states: {e}")
    
    async def _check_alarm_states(self):
        """Check the state of all CloudWatch alarms"""
        if not self.cloudwatch:
            return
        
        try:
            # Get all alarms for this service
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=f"{self.service_name}-"
            )
            
            for alarm in response.get('MetricAlarms', []):
                alarm_name = alarm['AlarmName']
                state = AlertState(alarm['StateValue'])
                
                # Check if this is a state change
                if alarm_name in self.active_alerts:
                    current_alert = self.active_alerts[alarm_name]
                    if current_alert.state != state:
                        # State change detected
                        await self._handle_state_change(alarm, state)
                else:
                    # New alert or first check
                    if state == AlertState.ALARM:
                        await self._handle_new_alert(alarm)
                
        except Exception as e:
            logger.error(f"Error checking alarm states: {e}")
    
    async def _handle_new_alert(self, alarm: Dict[str, Any]):
        """Handle a new alert"""
        alarm_name = alarm['AlarmName']
        
        # Find the corresponding alert rule
        rule = None
        for r in self.alert_rules:
            if f"{self.service_name}-{r.name}" == alarm_name:
                rule = r
                break
        
        if not rule:
            logger.warning(f"No rule found for alarm: {alarm_name}")
            return
        
        # Check if alert is suppressed
        if self._is_alert_suppressed(alarm_name):
            logger.info(f"Alert {alarm_name} is suppressed")
            return
        
        # Create alert notification
        notification = AlertNotification(
            alert_name=alarm_name,
            severity=rule.severity,
            state=AlertState.ALARM,
            timestamp=datetime.utcnow(),
            message=f"{rule.description}. Threshold: {rule.threshold}, Current: {alarm.get('StateReason', 'Unknown')}",
            metric_data={
                'metric_name': rule.metric_name,
                'namespace': rule.namespace,
                'threshold': rule.threshold,
                'comparison_operator': rule.comparison_operator
            },
            runbook_url=self._get_runbook_url(rule.name)
        )
        
        self.active_alerts[alarm_name] = notification
        self.alert_history.append(notification)
        
        # Send notifications
        await self._send_notification(notification, rule.notification_channels)
        
        logger.warning(f"New alert triggered: {alarm_name} - {rule.severity.value}")
    
    async def _handle_state_change(self, alarm: Dict[str, Any], new_state: AlertState):
        """Handle alert state change"""
        alarm_name = alarm['AlarmName']
        
        if alarm_name in self.active_alerts:
            current_alert = self.active_alerts[alarm_name]
            
            if new_state == AlertState.OK:
                # Alert resolved
                resolution_notification = AlertNotification(
                    alert_name=alarm_name,
                    severity=current_alert.severity,
                    state=AlertState.OK,
                    timestamp=datetime.utcnow(),
                    message=f"Alert resolved: {current_alert.message}",
                    metric_data=current_alert.metric_data
                )
                
                self.alert_history.append(resolution_notification)
                del self.active_alerts[alarm_name]
                
                # Send resolution notification
                await self._send_resolution_notification(resolution_notification)
                
                logger.info(f"Alert resolved: {alarm_name}")
            
            else:
                # Update alert state
                current_alert.state = new_state
                current_alert.timestamp = datetime.utcnow()
    
    async def _process_escalations(self):
        """Process alert escalations"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._check_escalations()
            except Exception as e:
                logger.error(f"Error processing escalations: {e}")
    
    async def _check_escalations(self):
        """Check for alerts that need escalation"""
        current_time = datetime.utcnow()
        
        for alert_name, alert in list(self.active_alerts.items()):
            if alert.state != AlertState.ALARM:
                continue
            
            severity = alert.severity.value
            if severity not in self.escalation_policies:
                continue
            
            policy = self.escalation_policies[severity]
            escalation_time = timedelta(minutes=policy['escalation_time_minutes'])
            
            if policy['escalation_time_minutes'] > 0 and current_time - alert.timestamp >= escalation_time:
                # Check if we haven't exceeded max escalations
                escalation_count = getattr(alert, 'escalation_count', 0)
                if escalation_count < policy['max_escalations']:
                    await self._escalate_alert(alert, policy['escalation_channels'])
                    alert.escalation_count = escalation_count + 1
    
    async def _escalate_alert(self, alert: AlertNotification, channels: List[str]):
        """Escalate an alert to additional channels"""
        escalation_message = f"ESCALATION: {alert.message} (Alert duration: {datetime.utcnow() - alert.timestamp})"
        
        escalated_notification = AlertNotification(
            alert_name=f"ESCALATED-{alert.alert_name}",
            severity=alert.severity,
            state=alert.state,
            timestamp=datetime.utcnow(),
            message=escalation_message,
            metric_data=alert.metric_data,
            runbook_url=alert.runbook_url
        )
        
        await self._send_notification(escalated_notification, channels)
        logger.warning(f"Alert escalated: {alert.alert_name}")
    
    async def _send_notification(self, notification: AlertNotification, channels: List[str]):
        """Send alert notification to specified channels"""
        for channel in channels:
            if channel in self.notification_channels:
                try:
                    await self.notification_channels[channel](notification)
                except Exception as e:
                    logger.error(f"Failed to send notification to {channel}: {e}")
    
    async def _send_resolution_notification(self, notification: AlertNotification):
        """Send alert resolution notification"""
        # Send to email by default for resolution notifications
        try:
            await self._send_email_notification(notification)
        except Exception as e:
            logger.error(f"Failed to send resolution notification: {e}")
    
    async def _send_email_notification(self, notification: AlertNotification):
        """Send email notification via SNS"""
        if not self.sns or not self.sns_topic_arn:
            logger.warning("SNS not configured for email notifications")
            return
        
        subject = f"[{notification.severity.value}] {self.service_name} Alert: {notification.alert_name}"
        
        message = f"""
Alert Details:
- Service: {self.service_name}
- Alert: {notification.alert_name}
- Severity: {notification.severity.value}
- State: {notification.state.value}
- Time: {notification.timestamp}
- Message: {notification.message}

Metric Information:
- Metric: {notification.metric_data.get('metric_name', 'Unknown')}
- Namespace: {notification.metric_data.get('namespace', 'Unknown')}
- Threshold: {notification.metric_data.get('threshold', 'Unknown')}
- Comparison: {notification.metric_data.get('comparison_operator', 'Unknown')}

{f'Runbook: {notification.runbook_url}' if notification.runbook_url else ''}

This is an automated alert from the AI Nutritionist monitoring system.
        """
        
        try:
            self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=message.strip()
            )
        except Exception as e:
            logger.error(f"Failed to send SNS notification: {e}")
    
    async def _send_slack_notification(self, notification: AlertNotification):
        """Send Slack notification (placeholder)"""
        # Implement Slack webhook integration
        logger.info(f"Slack notification: {notification.alert_name} - {notification.severity.value}")
    
    async def _send_pagerduty_notification(self, notification: AlertNotification):
        """Send PagerDuty notification (placeholder)"""
        # Implement PagerDuty API integration
        logger.warning(f"PagerDuty notification: {notification.alert_name} - {notification.severity.value}")
    
    async def _send_sms_notification(self, notification: AlertNotification):
        """Send SMS notification via SNS"""
        # Implement SMS via SNS
        logger.warning(f"SMS notification: {notification.alert_name} - {notification.severity.value}")
    
    def _is_alert_suppressed(self, alert_name: str) -> bool:
        """Check if an alert is currently suppressed"""
        if alert_name in self.suppression_rules:
            suppression_end = self.suppression_rules[alert_name]
            if datetime.utcnow() < suppression_end:
                return True
            else:
                del self.suppression_rules[alert_name]
        return False
    
    def _get_runbook_url(self, alert_name: str) -> Optional[str]:
        """Get runbook URL for an alert"""
        # Return documentation URLs for common alerts
        runbook_urls = {
            'high-response-time': 'https://docs.ai-nutritionist.com/runbooks/high-response-time',
            'high-error-rate': 'https://docs.ai-nutritionist.com/runbooks/high-error-rate',
            'high-cpu-utilization': 'https://docs.ai-nutritionist.com/runbooks/high-cpu',
            'high-memory-utilization': 'https://docs.ai-nutritionist.com/runbooks/high-memory',
            'disk-space-low': 'https://docs.ai-nutritionist.com/runbooks/disk-space',
            'dynamodb-throttles': 'https://docs.ai-nutritionist.com/runbooks/dynamodb-throttles'
        }
        return runbook_urls.get(alert_name)
    
    def suppress_alert(self, alert_name: str, duration_minutes: int):
        """Suppress an alert for a specified duration"""
        suppression_end = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.suppression_rules[alert_name] = suppression_end
        logger.info(f"Alert {alert_name} suppressed until {suppression_end}")
    
    async def _cleanup_old_alerts(self):
        """Clean up old alert history"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.timestamp > cutoff_time
                ]
                
                logger.debug("Cleaned up old alert history")
                
            except Exception as e:
                logger.error(f"Error cleaning up alert history: {e}")
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get comprehensive alert summary"""
        active_count = len(self.active_alerts)
        critical_count = len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL])
        high_count = len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.HIGH])
        
        # Recent alert history (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_alerts = [a for a in self.alert_history if a.timestamp > day_ago]
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name,
            'active_alerts': active_count,
            'critical_alerts': critical_count,
            'high_priority_alerts': high_count,
            'total_alert_rules': len(self.alert_rules),
            'alerts_last_24h': len(recent_alerts),
            'suppressed_alerts': len(self.suppression_rules),
            'active_alert_details': [
                {
                    'name': alert.alert_name,
                    'severity': alert.severity.value,
                    'duration_minutes': int((datetime.utcnow() - alert.timestamp).total_seconds() / 60),
                    'message': alert.message
                } for alert in list(self.active_alerts.values())[:10]
            ],
            'recent_resolutions': [
                {
                    'name': alert.alert_name,
                    'severity': alert.severity.value,
                    'resolved_at': alert.timestamp.isoformat()
                } for alert in recent_alerts if alert.state == AlertState.OK
            ][-10:]
        }


# Global alert manager
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(service_name: str = "ai-nutritionist") -> AlertManager:
    """Get or create global alert manager"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(service_name)
    return _alert_manager


def setup_alert_management(service_name: str, **kwargs) -> AlertManager:
    """Setup alert management"""
    global _alert_manager
    _alert_manager = AlertManager(service_name, **kwargs)
    return _alert_manager
