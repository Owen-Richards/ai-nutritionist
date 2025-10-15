"""
Health Monitoring and Metrics Integration

Provides integration with monitoring systems like CloudWatch and Prometheus.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import logging

import boto3
from botocore.exceptions import ClientError

try:
    from prometheus_client import Gauge, Counter, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from .core import HealthChecker, HealthStatus, ServiceHealth, HealthCheckResult

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """Health metrics data structure"""
    service_name: str
    timestamp: datetime
    overall_status: HealthStatus
    check_count: int
    healthy_checks: int
    unhealthy_checks: int
    degraded_checks: int
    average_response_time_ms: float
    uptime_seconds: float
    health_score: float
    details: Dict[str, Any] = field(default_factory=dict)


class HealthMonitor:
    """
    Monitors health checks and aggregates metrics
    """
    
    def __init__(
        self,
        health_checker: HealthChecker,
        monitoring_interval: int = 30,
        retention_hours: int = 24
    ):
        self.health_checker = health_checker
        self.monitoring_interval = monitoring_interval
        self.retention_hours = retention_hours
        
        # Metrics storage
        self._metrics_history: List[HealthMetrics] = []
        self._alerts: List[Dict[str, Any]] = []
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Alert thresholds
        self.alert_config = {
            'consecutive_failures': 3,
            'failure_rate_threshold': 0.5,  # 50%
            'response_time_threshold': 5000,  # 5 seconds
            'health_score_threshold': 80  # 80%
        }
        
        # Callbacks
        self._alert_callbacks: List[Callable] = []
        
        logger.info(f"Health monitor initialized for {health_checker.service_name}")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for health alerts"""
        self._alert_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._monitoring_active:
            logger.warning("Health monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Perform health check
                health_results = await self.health_checker.check_all()
                
                # Calculate metrics
                metrics = self._calculate_metrics(health_results)
                
                # Store metrics
                self._store_metrics(metrics)
                
                # Check for alerts
                await self._check_alerts(metrics)
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
            
            # Wait for next check
            await asyncio.sleep(self.monitoring_interval)
    
    def _calculate_metrics(self, health_results: Dict[str, ServiceHealth]) -> HealthMetrics:
        """Calculate aggregated health metrics"""
        total_checks = 0
        healthy_checks = 0
        unhealthy_checks = 0
        degraded_checks = 0
        total_response_time = 0.0
        
        # Aggregate across all check types
        for check_type, service_health in health_results.items():
            for check_result in service_health.checks:
                total_checks += 1
                total_response_time += check_result.duration_ms
                
                if check_result.status == HealthStatus.HEALTHY:
                    healthy_checks += 1
                elif check_result.status == HealthStatus.UNHEALTHY:
                    unhealthy_checks += 1
                elif check_result.status == HealthStatus.DEGRADED:
                    degraded_checks += 1
        
        # Calculate overall status
        if unhealthy_checks > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_checks > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate health score (0-100)
        if total_checks > 0:
            health_score = (healthy_checks + degraded_checks * 0.5) / total_checks * 100
            average_response_time = total_response_time / total_checks
        else:
            health_score = 100.0
            average_response_time = 0.0
        
        return HealthMetrics(
            service_name=self.health_checker.service_name,
            timestamp=datetime.utcnow(),
            overall_status=overall_status,
            check_count=total_checks,
            healthy_checks=healthy_checks,
            unhealthy_checks=unhealthy_checks,
            degraded_checks=degraded_checks,
            average_response_time_ms=average_response_time,
            uptime_seconds=self.health_checker._get_uptime(),
            health_score=health_score,
            details={
                'check_types': list(health_results.keys()),
                'startup_completed': self.health_checker.is_startup_completed()
            }
        )
    
    def _store_metrics(self, metrics: HealthMetrics):
        """Store metrics in history"""
        self._metrics_history.append(metrics)
        
        # Log metrics
        logger.info(
            f"Health metrics: status={metrics.overall_status.value}, "
            f"score={metrics.health_score:.1f}%, "
            f"checks={metrics.healthy_checks}/{metrics.check_count}, "
            f"avg_response={metrics.average_response_time_ms:.1f}ms"
        )
    
    async def _check_alerts(self, metrics: HealthMetrics):
        """Check for alert conditions"""
        alerts = []
        
        # Consecutive failures
        recent_metrics = self._metrics_history[-self.alert_config['consecutive_failures']:]
        if len(recent_metrics) >= self.alert_config['consecutive_failures']:
            if all(m.overall_status == HealthStatus.UNHEALTHY for m in recent_metrics):
                alerts.append({
                    'type': 'consecutive_failures',
                    'severity': 'critical',
                    'message': f"Service unhealthy for {len(recent_metrics)} consecutive checks",
                    'metrics': metrics
                })
        
        # High failure rate
        if metrics.check_count > 0:
            failure_rate = metrics.unhealthy_checks / metrics.check_count
            if failure_rate >= self.alert_config['failure_rate_threshold']:
                alerts.append({
                    'type': 'high_failure_rate',
                    'severity': 'warning',
                    'message': f"High failure rate: {failure_rate:.1%}",
                    'metrics': metrics
                })
        
        # High response time
        if metrics.average_response_time_ms >= self.alert_config['response_time_threshold']:
            alerts.append({
                'type': 'high_response_time',
                'severity': 'warning',
                'message': f"High average response time: {metrics.average_response_time_ms:.1f}ms",
                'metrics': metrics
            })
        
        # Low health score
        if metrics.health_score < self.alert_config['health_score_threshold']:
            alerts.append({
                'type': 'low_health_score',
                'severity': 'warning',
                'message': f"Low health score: {metrics.health_score:.1f}%",
                'metrics': metrics
            })
        
        # Process alerts
        for alert in alerts:
            await self._process_alert(alert)
    
    async def _process_alert(self, alert: Dict[str, Any]):
        """Process and send alert"""
        alert['timestamp'] = datetime.utcnow()
        alert['service_name'] = self.health_checker.service_name
        
        self._alerts.append(alert)
        
        logger.warning(f"Health alert: {alert['type']} - {alert['message']}")
        
        # Call alert callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def _cleanup_old_metrics(self):
        """Remove old metrics beyond retention period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        self._metrics_history = [
            m for m in self._metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        # Also clean up old alerts
        self._alerts = [
            a for a in self._alerts 
            if a['timestamp'] > cutoff_time
        ]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of health metrics"""
        if not self._metrics_history:
            return {'status': 'no_data'}
        
        latest = self._metrics_history[-1]
        recent_metrics = self._metrics_history[-10:]  # Last 10 checks
        
        # Calculate trends
        avg_health_score = sum(m.health_score for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.average_response_time_ms for m in recent_metrics) / len(recent_metrics)
        
        return {
            'current_status': latest.overall_status.value,
            'current_health_score': latest.health_score,
            'current_response_time_ms': latest.average_response_time_ms,
            'uptime_seconds': latest.uptime_seconds,
            'recent_avg_health_score': avg_health_score,
            'recent_avg_response_time_ms': avg_response_time,
            'total_metrics_collected': len(self._metrics_history),
            'active_alerts': len([a for a in self._alerts if a['timestamp'] > datetime.utcnow() - timedelta(hours=1)]),
            'monitoring_active': self._monitoring_active,
            'last_check': latest.timestamp.isoformat() + 'Z'
        }


class CloudWatchHealthReporter:
    """Reports health metrics to AWS CloudWatch"""
    
    def __init__(
        self,
        namespace: str = "HealthCheck",
        region: str = "us-east-1"
    ):
        self.namespace = namespace
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
    
    async def report_metrics(self, metrics: HealthMetrics):
        """Report health metrics to CloudWatch"""
        try:
            metric_data = [
                {
                    'MetricName': 'HealthScore',
                    'Dimensions': [
                        {'Name': 'ServiceName', 'Value': metrics.service_name}
                    ],
                    'Value': metrics.health_score,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'HealthyChecks',
                    'Dimensions': [
                        {'Name': 'ServiceName', 'Value': metrics.service_name}
                    ],
                    'Value': metrics.healthy_checks,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'UnhealthyChecks',
                    'Dimensions': [
                        {'Name': 'ServiceName', 'Value': metrics.service_name}
                    ],
                    'Value': metrics.unhealthy_checks,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'AverageResponseTime',
                    'Dimensions': [
                        {'Name': 'ServiceName', 'Value': metrics.service_name}
                    ],
                    'Value': metrics.average_response_time_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'ServiceUptime',
                    'Dimensions': [
                        {'Name': 'ServiceName', 'Value': metrics.service_name}
                    ],
                    'Value': metrics.uptime_seconds,
                    'Unit': 'Seconds',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            # Send metrics in batches (CloudWatch limit is 20 per call)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.debug(f"Reported {len(metric_data)} metrics to CloudWatch")
            
        except ClientError as e:
            logger.error(f"Failed to report metrics to CloudWatch: {e}")
        except Exception as e:
            logger.error(f"Error reporting metrics to CloudWatch: {e}")
    
    def create_alarms(self, service_name: str) -> List[str]:
        """Create CloudWatch alarms for health metrics"""
        alarms_created = []
        
        try:
            # Health Score Alarm
            alarm_name = f"{service_name}-LowHealthScore"
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='LessThanThreshold',
                EvaluationPeriods=2,
                MetricName='HealthScore',
                Namespace=self.namespace,
                Period=300,  # 5 minutes
                Statistic='Average',
                Threshold=80.0,
                ActionsEnabled=True,
                AlarmDescription=f'Health score below 80% for {service_name}',
                Dimensions=[
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                Unit='Percent'
            )
            alarms_created.append(alarm_name)
            
            # High Response Time Alarm
            alarm_name = f"{service_name}-HighResponseTime"
            self.cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='AverageResponseTime',
                Namespace=self.namespace,
                Period=300,
                Statistic='Average',
                Threshold=5000.0,  # 5 seconds
                ActionsEnabled=True,
                AlarmDescription=f'High response time for {service_name}',
                Dimensions=[
                    {'Name': 'ServiceName', 'Value': service_name}
                ],
                Unit='Milliseconds'
            )
            alarms_created.append(alarm_name)
            
            logger.info(f"Created CloudWatch alarms: {alarms_created}")
            
        except ClientError as e:
            logger.error(f"Failed to create CloudWatch alarms: {e}")
        except Exception as e:
            logger.error(f"Error creating CloudWatch alarms: {e}")
        
        return alarms_created


class PrometheusHealthReporter:
    """Reports health metrics to Prometheus"""
    
    def __init__(self, port: int = 8000):
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client not available")
        
        self.port = port
        
        # Create Prometheus metrics
        self.health_score_gauge = Gauge(
            'health_score',
            'Overall health score percentage',
            ['service_name']
        )
        
        self.healthy_checks_gauge = Gauge(
            'healthy_checks_total',
            'Number of healthy checks',
            ['service_name']
        )
        
        self.unhealthy_checks_gauge = Gauge(
            'unhealthy_checks_total',
            'Number of unhealthy checks',
            ['service_name']
        )
        
        self.response_time_histogram = Histogram(
            'health_check_duration_seconds',
            'Health check response time',
            ['service_name', 'check_name', 'check_type']
        )
        
        self.uptime_gauge = Gauge(
            'service_uptime_seconds',
            'Service uptime in seconds',
            ['service_name']
        )
        
        # Start HTTP server for metrics
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    
    def report_metrics(self, metrics: HealthMetrics):
        """Report health metrics to Prometheus"""
        try:
            labels = {'service_name': metrics.service_name}
            
            self.health_score_gauge.labels(**labels).set(metrics.health_score)
            self.healthy_checks_gauge.labels(**labels).set(metrics.healthy_checks)
            self.unhealthy_checks_gauge.labels(**labels).set(metrics.unhealthy_checks)
            self.uptime_gauge.labels(**labels).set(metrics.uptime_seconds)
            
            logger.debug(f"Updated Prometheus metrics for {metrics.service_name}")
            
        except Exception as e:
            logger.error(f"Error reporting metrics to Prometheus: {e}")
    
    def report_check_result(self, result: HealthCheckResult):
        """Report individual check result to Prometheus"""
        try:
            labels = {
                'service_name': result.service_name,
                'check_name': result.check_name,
                'check_type': result.check_type.value
            }
            
            # Record response time
            self.response_time_histogram.labels(**labels).observe(result.duration_ms / 1000.0)
            
        except Exception as e:
            logger.error(f"Error reporting check result to Prometheus: {e}")
