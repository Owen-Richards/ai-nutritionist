"""
Error Metrics and Analytics

Provides comprehensive error tracking, metrics collection,
and analytics for monitoring and improving system reliability.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import boto3
from botocore.exceptions import ClientError

from .exceptions import BaseError, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)


@dataclass
class ErrorMetric:
    """Single error metric data point"""
    error_id: str
    error_code: str
    category: str
    severity: str
    timestamp: datetime
    operation: Optional[str] = None
    service: Optional[str] = None
    user_id: Optional[str] = None
    duration_ms: Optional[float] = None
    resolved: bool = False
    resolution_time_ms: Optional[float] = None


@dataclass
class ErrorTrend:
    """Error trend analysis data"""
    time_window: str
    total_errors: int
    error_rate: float
    category_distribution: Dict[str, int] = field(default_factory=dict)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    top_error_codes: List[Tuple[str, int]] = field(default_factory=list)
    most_affected_operations: List[Tuple[str, int]] = field(default_factory=list)


class ErrorMetricsCollector:
    """
    Comprehensive error metrics collection and analysis
    
    Collects, stores, and analyzes error metrics for monitoring,
    alerting, and system improvement.
    """
    
    def __init__(self):
        # AWS services for metrics and storage
        self.cloudwatch = boto3.client('cloudwatch')
        self.dynamodb = boto3.resource('dynamodb')
        
        # Error storage table
        try:
            self.error_table = self.dynamodb.Table('ai-nutritionist-error-metrics')
        except ClientError:
            logger.warning("Error metrics table not found, metrics will be logged only")
            self.error_table = None
        
        # In-memory metrics for real-time analysis
        self.recent_errors = deque(maxlen=1000)  # Last 1000 errors
        self.error_counts = defaultdict(int)
        self.operation_errors = defaultdict(int)
        self.service_errors = defaultdict(int)
        
        # Performance tracking
        self.last_cleanup = datetime.utcnow()
        self.metrics_sent = 0
    
    def record_error(
        self,
        error: BaseError,
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        service: Optional[str] = None,
        user_id: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """
        Record an error occurrence
        
        Args:
            error: The error that occurred
            context: Additional context information
            operation: Operation where error occurred
            service: Service where error occurred
            user_id: User associated with the error
            duration_ms: Duration of the failed operation
        """
        try:
            # Create error metric
            metric = ErrorMetric(
                error_id=error.error_id,
                error_code=error.error_code,
                category=error.category.value,
                severity=error.severity.value,
                timestamp=error.timestamp,
                operation=operation or error.context.get('operation'),
                service=service or error.context.get('service_name'),
                user_id=user_id or error.context.get('user_id'),
                duration_ms=duration_ms
            )
            
            # Store in memory for real-time analysis
            self.recent_errors.append(metric)
            self.error_counts[error.error_code] += 1
            
            if metric.operation:
                self.operation_errors[metric.operation] += 1
            if metric.service:
                self.service_errors[metric.service] += 1
            
            # Send to CloudWatch
            asyncio.create_task(self._send_cloudwatch_metrics(metric, error))
            
            # Store in DynamoDB for historical analysis
            if self.error_table:
                asyncio.create_task(self._store_error_metric(metric, error, context))
            
            # Check for alert conditions
            self._check_alert_conditions(metric)
            
        except Exception as e:
            logger.error(f"Failed to record error metric: {e}")
    
    async def _send_cloudwatch_metrics(self, metric: ErrorMetric, error: BaseError):
        """Send metrics to CloudWatch"""
        try:
            metric_data = [
                {
                    'MetricName': 'ErrorOccurrence',
                    'Dimensions': [
                        {'Name': 'ErrorCategory', 'Value': metric.category},
                        {'Name': 'ErrorSeverity', 'Value': metric.severity}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metric.timestamp
                },
                {
                    'MetricName': 'ErrorsByCode',
                    'Dimensions': [
                        {'Name': 'ErrorCode', 'Value': metric.error_code}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metric.timestamp
                }
            ]
            
            # Add operation-specific metrics
            if metric.operation:
                metric_data.append({
                    'MetricName': 'OperationErrors',
                    'Dimensions': [
                        {'Name': 'Operation', 'Value': metric.operation},
                        {'Name': 'ErrorCategory', 'Value': metric.category}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metric.timestamp
                })
            
            # Add service-specific metrics
            if metric.service:
                metric_data.append({
                    'MetricName': 'ServiceErrors',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metric.service},
                        {'Name': 'ErrorSeverity', 'Value': metric.severity}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metric.timestamp
                })
            
            # Add duration metric if available
            if metric.duration_ms:
                metric_data.append({
                    'MetricName': 'ErrorDuration',
                    'Dimensions': [
                        {'Name': 'Operation', 'Value': metric.operation or 'unknown'}
                    ],
                    'Value': metric.duration_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': metric.timestamp
                })
            
            # Send to CloudWatch
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.cloudwatch.put_metric_data(
                    Namespace='AINutritionist/Errors',
                    MetricData=metric_data
                )
            )
            
            self.metrics_sent += len(metric_data)
            
        except Exception as e:
            logger.error(f"Failed to send CloudWatch metrics: {e}")
    
    async def _store_error_metric(self, metric: ErrorMetric, error: BaseError, context: Optional[Dict[str, Any]]):
        """Store error metric in DynamoDB for historical analysis"""
        try:
            item = {
                'error_id': metric.error_id,
                'timestamp': metric.timestamp.isoformat(),
                'ttl': int((metric.timestamp + timedelta(days=90)).timestamp()),  # 90-day retention
                'error_code': metric.error_code,
                'category': metric.category,
                'severity': metric.severity,
                'message': error.message,
                'user_message': error.user_message,
                'recoverable': error.recoverable,
                'retry_after': error.retry_after,
                'error_context': error.context,
                'additional_context': context or {}
            }
            
            # Add optional fields
            if metric.operation:
                item['operation'] = metric.operation
            if metric.service:
                item['service'] = metric.service
            if metric.user_id:
                item['user_id'] = metric.user_id
            if metric.duration_ms:
                item['duration_ms'] = metric.duration_ms
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.error_table.put_item(Item=item)
            )
            
        except Exception as e:
            logger.error(f"Failed to store error metric in DynamoDB: {e}")
    
    def record_success(self, operation: str, duration_ms: float, attempts: int = 1):
        """Record successful operation for error rate calculation"""
        try:
            asyncio.create_task(self._send_success_metrics(operation, duration_ms, attempts))
        except Exception as e:
            logger.error(f"Failed to record success metric: {e}")
    
    async def _send_success_metrics(self, operation: str, duration_ms: float, attempts: int):
        """Send success metrics to CloudWatch"""
        try:
            metric_data = [
                {
                    'MetricName': 'OperationSuccess',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': 1,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'OperationDuration',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': duration_ms,
                    'Unit': 'Milliseconds'
                }
            ]
            
            if attempts > 1:
                metric_data.append({
                    'MetricName': 'OperationRetries',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': attempts - 1,
                    'Unit': 'Count'
                })
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.cloudwatch.put_metric_data(
                    Namespace='AINutritionist/Operations',
                    MetricData=metric_data
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to send success metrics: {e}")
    
    def record_function_error(self, function_name: str, error: BaseError):
        """Record error from function decorator"""
        self.record_error(
            error=error,
            operation=function_name,
            context={'source': 'function_decorator'}
        )
    
    async def record_function_error_async(self, function_name: str, error: BaseError):
        """Async version of record_function_error"""
        self.record_function_error(function_name, error)
    
    def record_critical_failure(self, operation: str, error: Exception, attempts: int):
        """Record critical failure that exhausted all recovery attempts"""
        try:
            # Send critical alert metric
            asyncio.create_task(self._send_critical_alert_metric(operation, error, attempts))
            
            # Log critical failure
            logger.critical(
                f"Critical failure in {operation} after {attempts} attempts: {error}",
                extra={
                    'operation': operation,
                    'attempts': attempts,
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to record critical failure: {e}")
    
    async def _send_critical_alert_metric(self, operation: str, error: Exception, attempts: int):
        """Send critical alert metric to CloudWatch"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.cloudwatch.put_metric_data(
                    Namespace='AINutritionist/Alerts',
                    MetricData=[
                        {
                            'MetricName': 'CriticalFailure',
                            'Dimensions': [
                                {'Name': 'Operation', 'Value': operation},
                                {'Name': 'ErrorType', 'Value': type(error).__name__}
                            ],
                            'Value': 1,
                            'Unit': 'Count'
                        },
                        {
                            'MetricName': 'FailureAttempts',
                            'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                            'Value': attempts,
                            'Unit': 'Count'
                        }
                    ]
                )
            )
        except Exception as e:
            logger.error(f"Failed to send critical alert metric: {e}")
    
    def _check_alert_conditions(self, metric: ErrorMetric):
        """Check if error conditions warrant alerts"""
        try:
            # Check for high error rates
            recent_errors = [e for e in self.recent_errors if e.timestamp > datetime.utcnow() - timedelta(minutes=5)]
            
            if len(recent_errors) > 50:  # More than 50 errors in 5 minutes
                logger.warning(f"High error rate detected: {len(recent_errors)} errors in 5 minutes")
            
            # Check for critical errors
            if metric.severity == ErrorSeverity.CRITICAL.value:
                logger.critical(f"Critical error detected: {metric.error_code}")
            
            # Check for operation-specific issues
            if metric.operation:
                operation_recent_errors = [
                    e for e in recent_errors 
                    if e.operation == metric.operation
                ]
                if len(operation_recent_errors) > 10:  # More than 10 errors for same operation
                    logger.warning(
                        f"High error rate for operation {metric.operation}: "
                        f"{len(operation_recent_errors)} errors in 5 minutes"
                    )
            
        except Exception as e:
            logger.error(f"Failed to check alert conditions: {e}")
    
    def get_error_analytics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive error analytics
        
        Args:
            time_window_hours: Hours to analyze (default 24)
        
        Returns:
            Analytics data including trends, patterns, and insights
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            recent_errors = [e for e in self.recent_errors if e.timestamp > cutoff_time]
            
            if not recent_errors:
                return {
                    'time_window_hours': time_window_hours,
                    'total_errors': 0,
                    'error_rate': 0,
                    'trends': [],
                    'insights': ['No errors in the specified time window']
                }
            
            # Calculate basic metrics
            total_errors = len(recent_errors)
            error_rate = total_errors / time_window_hours
            
            # Category distribution
            category_distribution = defaultdict(int)
            severity_distribution = defaultdict(int)
            operation_distribution = defaultdict(int)
            service_distribution = defaultdict(int)
            hourly_distribution = defaultdict(int)
            
            for error in recent_errors:
                category_distribution[error.category] += 1
                severity_distribution[error.severity] += 1
                if error.operation:
                    operation_distribution[error.operation] += 1
                if error.service:
                    service_distribution[error.service] += 1
                
                # Hourly distribution
                hour_key = error.timestamp.strftime('%Y-%m-%d %H:00')
                hourly_distribution[hour_key] += 1
            
            # Top error codes
            error_code_counts = defaultdict(int)
            for error in recent_errors:
                error_code_counts[error.error_code] += 1
            
            top_error_codes = sorted(
                error_code_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Generate insights
            insights = self._generate_insights(
                recent_errors,
                category_distribution,
                severity_distribution,
                operation_distribution
            )
            
            return {
                'time_window_hours': time_window_hours,
                'total_errors': total_errors,
                'error_rate': round(error_rate, 2),
                'category_distribution': dict(category_distribution),
                'severity_distribution': dict(severity_distribution),
                'top_error_codes': top_error_codes,
                'top_operations': sorted(operation_distribution.items(), key=lambda x: x[1], reverse=True)[:10],
                'top_services': sorted(service_distribution.items(), key=lambda x: x[1], reverse=True)[:10],
                'hourly_distribution': dict(hourly_distribution),
                'insights': insights,
                'recommendations': self._generate_recommendations(category_distribution, severity_distribution)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate error analytics: {e}")
            return {'error': 'Failed to generate analytics', 'details': str(e)}
    
    def _generate_insights(
        self,
        errors: List[ErrorMetric],
        categories: Dict[str, int],
        severities: Dict[str, int],
        operations: Dict[str, int]
    ) -> List[str]:
        """Generate insights from error data"""
        insights = []
        
        total_errors = len(errors)
        
        # Category insights
        if categories:
            top_category = max(categories, key=categories.get)
            category_percentage = (categories[top_category] / total_errors) * 100
            insights.append(
                f"Most common error category: {top_category} ({category_percentage:.1f}% of errors)"
            )
        
        # Severity insights
        if severities:
            critical_count = severities.get('critical', 0)
            high_count = severities.get('high', 0)
            if critical_count > 0:
                insights.append(f"Found {critical_count} critical errors requiring immediate attention")
            if high_count > 0:
                insights.append(f"Found {high_count} high-severity errors")
        
        # Operation insights
        if operations:
            top_operation = max(operations, key=operations.get)
            operation_percentage = (operations[top_operation] / total_errors) * 100
            if operation_percentage > 30:
                insights.append(
                    f"Operation '{top_operation}' accounts for {operation_percentage:.1f}% of errors"
                )
        
        # Trend insights
        if total_errors > 100:
            insights.append("High error volume detected - system may be under stress")
        elif total_errors < 5:
            insights.append("Low error rate - system operating normally")
        
        return insights
    
    def _generate_recommendations(
        self,
        categories: Dict[str, int],
        severities: Dict[str, int]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Category-based recommendations
        if categories.get('infrastructure', 0) > categories.get('validation', 0):
            recommendations.append("Focus on infrastructure stability and service reliability")
        
        if categories.get('validation', 0) > 10:
            recommendations.append("Review input validation logic and error handling")
        
        if categories.get('rate_limiting', 0) > 5:
            recommendations.append("Consider adjusting rate limits or implementing caching")
        
        # Severity-based recommendations
        if severities.get('critical', 0) > 0:
            recommendations.append("Investigate and resolve critical errors immediately")
        
        if severities.get('high', 0) > severities.get('low', 0):
            recommendations.append("Prioritize fixing high-severity errors")
        
        # General recommendations
        if sum(categories.values()) > 50:
            recommendations.append("Consider implementing circuit breakers for frequently failing operations")
            recommendations.append("Review monitoring and alerting thresholds")
        
        return recommendations
    
    def get_error_trends(self, days: int = 7) -> List[ErrorTrend]:
        """Get error trends over time"""
        trends = []
        
        for day_offset in range(days):
            start_time = datetime.utcnow() - timedelta(days=day_offset + 1)
            end_time = datetime.utcnow() - timedelta(days=day_offset)
            
            day_errors = [
                e for e in self.recent_errors
                if start_time <= e.timestamp < end_time
            ]
            
            if day_errors:
                category_dist = defaultdict(int)
                severity_dist = defaultdict(int)
                error_code_counts = defaultdict(int)
                operation_counts = defaultdict(int)
                
                for error in day_errors:
                    category_dist[error.category] += 1
                    severity_dist[error.severity] += 1
                    error_code_counts[error.error_code] += 1
                    if error.operation:
                        operation_counts[error.operation] += 1
                
                trend = ErrorTrend(
                    time_window=start_time.strftime('%Y-%m-%d'),
                    total_errors=len(day_errors),
                    error_rate=len(day_errors) / 24,  # errors per hour
                    category_distribution=dict(category_dist),
                    severity_distribution=dict(severity_dist),
                    top_error_codes=sorted(error_code_counts.items(), key=lambda x: x[1], reverse=True)[:5],
                    most_affected_operations=sorted(operation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                )
                
                trends.append(trend)
        
        return trends
    
    def cleanup_old_metrics(self):
        """Clean up old metrics from memory"""
        try:
            # Remove errors older than 24 hours from memory
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Filter recent_errors
            self.recent_errors = deque(
                (e for e in self.recent_errors if e.timestamp > cutoff_time),
                maxlen=1000
            )
            
            # Reset counters periodically
            if (datetime.utcnow() - self.last_cleanup).total_seconds() > 3600:  # Every hour
                self.error_counts.clear()
                self.operation_errors.clear()
                self.service_errors.clear()
                self.last_cleanup = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")


class ErrorAnalytics:
    """
    Advanced error analytics and reporting
    
    Provides deep analysis, pattern detection, and reporting
    capabilities for error management.
    """
    
    def __init__(self, metrics_collector: ErrorMetricsCollector):
        self.metrics_collector = metrics_collector
    
    def detect_anomalies(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Detect error anomalies and unusual patterns"""
        try:
            analytics = self.metrics_collector.get_error_analytics(time_window_hours)
            
            anomalies = []
            
            # Check for error rate spikes
            if analytics['error_rate'] > 10:  # More than 10 errors per hour
                anomalies.append({
                    'type': 'high_error_rate',
                    'description': f"Error rate ({analytics['error_rate']}/hour) is unusually high",
                    'severity': 'high'
                })
            
            # Check for new error types
            top_errors = dict(analytics['top_error_codes'])
            for error_code, count in top_errors.items():
                if count > 5 and 'UNKNOWN' in error_code:
                    anomalies.append({
                        'type': 'new_error_type',
                        'description': f"New or unusual error type detected: {error_code}",
                        'severity': 'medium'
                    })
            
            # Check for service-specific issues
            service_errors = analytics.get('top_services', [])
            for service, count in service_errors[:3]:
                if count > analytics['total_errors'] * 0.5:
                    anomalies.append({
                        'type': 'service_specific_issue',
                        'description': f"Service '{service}' has {count} errors ({count/analytics['total_errors']*100:.1f}% of total)",
                        'severity': 'high'
                    })
            
            return {
                'anomalies_detected': len(anomalies),
                'anomalies': anomalies,
                'analysis_time_window': time_window_hours,
                'total_errors_analyzed': analytics['total_errors']
            }
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
            return {'error': 'Failed to detect anomalies', 'details': str(e)}
    
    def generate_error_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive error report"""
        try:
            analytics = self.metrics_collector.get_error_analytics(days * 24)
            trends = self.metrics_collector.get_error_trends(days)
            anomalies = self.detect_anomalies(days * 24)
            
            return {
                'report_period_days': days,
                'generated_at': datetime.utcnow().isoformat(),
                'summary': analytics,
                'trends': [
                    {
                        'date': trend.time_window,
                        'total_errors': trend.total_errors,
                        'error_rate': trend.error_rate,
                        'top_category': max(trend.category_distribution, key=trend.category_distribution.get) if trend.category_distribution else None
                    }
                    for trend in trends
                ],
                'anomalies': anomalies,
                'health_score': self._calculate_health_score(analytics),
                'action_items': self._generate_action_items(analytics, anomalies)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate error report: {e}")
            return {'error': 'Failed to generate report', 'details': str(e)}
    
    def _calculate_health_score(self, analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate system health score based on errors"""
        try:
            total_errors = analytics.get('total_errors', 0)
            error_rate = analytics.get('error_rate', 0)
            critical_errors = analytics.get('severity_distribution', {}).get('critical', 0)
            
            # Calculate score (0-100)
            score = 100
            
            # Penalize for error rate
            if error_rate > 5:
                score -= min(30, error_rate * 2)
            
            # Penalize for critical errors
            score -= critical_errors * 10
            
            # Penalize for high total errors
            if total_errors > 100:
                score -= min(20, (total_errors - 100) / 10)
            
            score = max(0, score)
            
            # Determine health status
            if score >= 90:
                status = 'excellent'
            elif score >= 75:
                status = 'good'
            elif score >= 50:
                status = 'fair'
            else:
                status = 'poor'
            
            return {
                'score': score,
                'status': status,
                'factors': {
                    'error_rate': error_rate,
                    'critical_errors': critical_errors,
                    'total_errors': total_errors
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}")
            return {'score': 0, 'status': 'unknown', 'error': str(e)}
    
    def _generate_action_items(self, analytics: Dict[str, Any], anomalies: Dict[str, Any]) -> List[str]:
        """Generate actionable items based on analysis"""
        action_items = []
        
        # Based on analytics
        if analytics.get('total_errors', 0) > 50:
            action_items.append("Investigate high error volume and implement preventive measures")
        
        critical_errors = analytics.get('severity_distribution', {}).get('critical', 0)
        if critical_errors > 0:
            action_items.append(f"Resolve {critical_errors} critical errors immediately")
        
        # Based on anomalies
        high_severity_anomalies = [a for a in anomalies.get('anomalies', []) if a.get('severity') == 'high']
        if high_severity_anomalies:
            action_items.append("Address high-severity anomalies detected in error patterns")
        
        # Based on top error codes
        top_errors = analytics.get('top_error_codes', [])
        if top_errors and top_errors[0][1] > 10:
            action_items.append(f"Focus on resolving top error: {top_errors[0][0]} ({top_errors[0][1]} occurrences)")
        
        return action_items
