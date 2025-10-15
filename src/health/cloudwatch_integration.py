"""
CloudWatch Health Monitoring Integration

Provides comprehensive CloudWatch integration for health monitoring including:
- Custom metrics and alarms
- Dashboard creation
- Automated incident response
- Performance tracking
"""

import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class HealthCheckCloudWatchIntegration:
    """
    CloudWatch integration for health check monitoring
    """
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        
        # Metric namespaces
        self.namespaces = {
            'system': 'AINutritionist/System/Health',
            'services': 'AINutritionist/Services/Health',
            'dependencies': 'AINutritionist/Dependencies/Health',
            'circuit_breakers': 'AINutritionist/CircuitBreakers'
        }
    
    async def create_health_dashboard(self) -> str:
        """Create comprehensive health monitoring dashboard"""
        
        dashboard_body = {
            "widgets": [
                # System Overview
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['system'], "SystemHealthScore", "System", "AINutritionist"],
                            [self.namespaces['system'], "HealthyServices", "System", "AINutritionist"],
                            [self.namespaces['system'], "UnhealthyServices", "System", "AINutritionist"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "System Health Overview",
                        "yAxis": {"left": {"min": 0, "max": 100}}
                    }
                },
                
                # Service Health Status
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['services'], "HealthScore", "Service", "nutrition-service"],
                            [self.namespaces['services'], "HealthScore", "Service", "messaging-service"],
                            [self.namespaces['services'], "HealthScore", "Service", "ai-coach-service"],
                            [self.namespaces['services'], "HealthScore", "Service", "payment-service"],
                            [self.namespaces['services'], "HealthScore", "Service", "health-tracking-service"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Service Health Scores",
                        "yAxis": {"left": {"min": 0, "max": 100}}
                    }
                },
                
                # Response Times
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['services'], "AverageResponseTime", "Service", "nutrition-service"],
                            [self.namespaces['services'], "AverageResponseTime", "Service", "messaging-service"],
                            [self.namespaces['services'], "AverageResponseTime", "Service", "ai-coach-service"],
                            [self.namespaces['services'], "AverageResponseTime", "Service", "payment-service"],
                            [self.namespaces['services'], "AverageResponseTime", "Service", "health-tracking-service"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Health Check Response Times (ms)",
                        "yAxis": {"left": {"min": 0}}
                    }
                },
                
                # Circuit Breaker Status
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['circuit_breakers'], "OpenCircuitBreakers", "System", "AINutritionist"],
                            [self.namespaces['circuit_breakers'], "TotalCircuitBreakers", "System", "AINutritionist"]
                        ],
                        "period": 300,
                        "stat": "Maximum",
                        "region": self.region,
                        "title": "Circuit Breaker Status"
                    }
                },
                
                # Dependency Health
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 24, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['dependencies'], "DependencyHealth", "Type", "Database"],
                            [self.namespaces['dependencies'], "DependencyHealth", "Type", "Redis"],
                            [self.namespaces['dependencies'], "DependencyHealth", "Type", "OpenAI"],
                            [self.namespaces['dependencies'], "DependencyHealth", "Type", "AWS"],
                            [self.namespaces['dependencies'], "DependencyHealth", "Type", "ExternalAPI"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Dependency Health Status",
                        "yAxis": {"left": {"min": 0, "max": 1}}
                    }
                },
                
                # Error Rate
                {
                    "type": "metric",
                    "x": 0, "y": 18, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['services'], "ErrorRate", "Service", "nutrition-service"],
                            [self.namespaces['services'], "ErrorRate", "Service", "messaging-service"],
                            [self.namespaces['services'], "ErrorRate", "Service", "ai-coach-service"],
                            [self.namespaces['services'], "ErrorRate", "Service", "payment-service"],
                            [self.namespaces['services'], "ErrorRate", "Service", "health-tracking-service"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Health Check Error Rates (%)",
                        "yAxis": {"left": {"min": 0}}
                    }
                },
                
                # System Uptime
                {
                    "type": "metric",
                    "x": 12, "y": 18, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespaces['system'], "SystemUptime", "System", "AINutritionist"]
                        ],
                        "period": 300,
                        "stat": "Maximum",
                        "region": self.region,
                        "title": "System Uptime (seconds)"
                    }
                }
            ]
        }
        
        try:
            dashboard_name = "AINutritionist-HealthMonitoring"
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            return dashboard_name
            
        except ClientError as e:
            logger.error(f"Failed to create CloudWatch dashboard: {e}")
            raise
    
    async def create_health_alarms(self) -> List[str]:
        """Create CloudWatch alarms for health monitoring"""
        
        alarms_created = []
        
        alarm_definitions = [
            # System-level alarms
            {
                'AlarmName': 'AINutritionist-SystemHealthScore-Low',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'SystemHealthScore',
                'Namespace': self.namespaces['system'],
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 80.0,
                'ActionsEnabled': True,
                'AlarmDescription': 'System health score below 80%',
                'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                'Unit': 'Percent',
                'TreatMissingData': 'breaching'
            },
            
            {
                'AlarmName': 'AINutritionist-UnhealthyServices-High',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'UnhealthyServices',
                'Namespace': self.namespaces['system'],
                'Period': 300,
                'Statistic': 'Maximum',
                'Threshold': 1.0,
                'ActionsEnabled': True,
                'AlarmDescription': 'One or more services are unhealthy',
                'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                'Unit': 'Count',
                'TreatMissingData': 'breaching'
            },
            
            # Circuit breaker alarms
            {
                'AlarmName': 'AINutritionist-CircuitBreakers-Open',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'OpenCircuitBreakers',
                'Namespace': self.namespaces['circuit_breakers'],
                'Period': 300,
                'Statistic': 'Maximum',
                'Threshold': 0.0,
                'ActionsEnabled': True,
                'AlarmDescription': 'One or more circuit breakers are open',
                'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                'Unit': 'Count',
                'TreatMissingData': 'notBreaching'
            }
        ]
        
        # Service-specific alarms
        services = ['nutrition-service', 'messaging-service', 'ai-coach-service', 
                   'payment-service', 'health-tracking-service']
        
        for service in services:
            # Health score alarm
            alarm_definitions.append({
                'AlarmName': f'AINutritionist-{service}-HealthScore-Low',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'HealthScore',
                'Namespace': self.namespaces['services'],
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 70.0,
                'ActionsEnabled': True,
                'AlarmDescription': f'{service} health score below 70%',
                'Dimensions': [{'Name': 'Service', 'Value': service}],
                'Unit': 'Percent',
                'TreatMissingData': 'breaching'
            })
            
            # Response time alarm
            alarm_definitions.append({
                'AlarmName': f'AINutritionist-{service}-ResponseTime-High',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'AverageResponseTime',
                'Namespace': self.namespaces['services'],
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 5000.0,  # 5 seconds
                'ActionsEnabled': True,
                'AlarmDescription': f'{service} response time above 5 seconds',
                'Dimensions': [{'Name': 'Service', 'Value': service}],
                'Unit': 'Milliseconds',
                'TreatMissingData': 'notBreaching'
            })
        
        # Create alarms
        for alarm_def in alarm_definitions:
            try:
                self.cloudwatch.put_metric_alarm(**alarm_def)
                alarms_created.append(alarm_def['AlarmName'])
                logger.info(f"Created alarm: {alarm_def['AlarmName']}")
            except ClientError as e:
                logger.error(f"Failed to create alarm {alarm_def['AlarmName']}: {e}")
        
        return alarms_created
    
    async def send_health_metrics(self, metrics: Dict[str, Any]):
        """Send health metrics to CloudWatch"""
        
        metric_data = []
        timestamp = datetime.utcnow()
        
        # System metrics
        if 'system' in metrics:
            system_metrics = metrics['system']
            
            metric_data.extend([
                {
                    'MetricName': 'SystemHealthScore',
                    'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                    'Value': system_metrics.get('health_score', 0),
                    'Unit': 'Percent',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'HealthyServices',
                    'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                    'Value': system_metrics.get('healthy_services', 0),
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'UnhealthyServices',
                    'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                    'Value': system_metrics.get('unhealthy_services', 0),
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'SystemUptime',
                    'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                    'Value': system_metrics.get('uptime_seconds', 0),
                    'Unit': 'Seconds',
                    'Timestamp': timestamp
                }
            ])
        
        # Service metrics
        if 'services' in metrics:
            for service_name, service_data in metrics['services'].items():
                metric_data.extend([
                    {
                        'MetricName': 'HealthScore',
                        'Dimensions': [{'Name': 'Service', 'Value': service_name}],
                        'Value': service_data.get('health_score', 0),
                        'Unit': 'Percent',
                        'Timestamp': timestamp
                    },
                    {
                        'MetricName': 'AverageResponseTime',
                        'Dimensions': [{'Name': 'Service', 'Value': service_name}],
                        'Value': service_data.get('avg_response_time_ms', 0),
                        'Unit': 'Milliseconds',
                        'Timestamp': timestamp
                    },
                    {
                        'MetricName': 'ErrorRate',
                        'Dimensions': [{'Name': 'Service', 'Value': service_name}],
                        'Value': service_data.get('error_rate', 0),
                        'Unit': 'Percent',
                        'Timestamp': timestamp
                    }
                ])
        
        # Circuit breaker metrics
        if 'circuit_breakers' in metrics:
            cb_data = metrics['circuit_breakers']
            metric_data.extend([
                {
                    'MetricName': 'OpenCircuitBreakers',
                    'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                    'Value': len(cb_data.get('open_breakers', [])),
                    'Unit': 'Count',
                    'Timestamp': timestamp
                },
                {
                    'MetricName': 'TotalCircuitBreakers',
                    'Dimensions': [{'Name': 'System', 'Value': 'AINutritionist'}],
                    'Value': cb_data.get('total_breakers', 0),
                    'Unit': 'Count',
                    'Timestamp': timestamp
                }
            ])
        
        # Dependency metrics
        if 'dependencies' in metrics:
            for dep_type, health_value in metrics['dependencies'].items():
                metric_data.append({
                    'MetricName': 'DependencyHealth',
                    'Dimensions': [{'Name': 'Type', 'Value': dep_type}],
                    'Value': 1 if health_value == 'healthy' else 0,
                    'Unit': 'None',
                    'Timestamp': timestamp
                })
        
        # Send metrics in batches
        batch_size = 20  # CloudWatch limit
        for i in range(0, len(metric_data), batch_size):
            batch = metric_data[i:i + batch_size]
            
            try:
                # Determine appropriate namespace
                namespace = self.namespaces['system']  # Default
                
                self.cloudwatch.put_metric_data(
                    Namespace=namespace,
                    MetricData=batch
                )
                
                logger.debug(f"Sent {len(batch)} metrics to CloudWatch")
                
            except ClientError as e:
                logger.error(f"Failed to send metrics batch to CloudWatch: {e}")
    
    async def create_log_groups(self) -> List[str]:
        """Create CloudWatch log groups for health monitoring"""
        
        log_groups = [
            '/aws/health-check/system',
            '/aws/health-check/nutrition-service',
            '/aws/health-check/messaging-service',
            '/aws/health-check/ai-coach-service',
            '/aws/health-check/payment-service',
            '/aws/health-check/health-tracking-service',
            '/aws/health-check/circuit-breakers'
        ]
        
        created_groups = []
        
        for log_group in log_groups:
            try:
                self.logs.create_log_group(
                    logGroupName=log_group,
                    tags={
                        'Application': 'AINutritionist',
                        'Component': 'HealthCheck',
                        'Environment': 'production'
                    }
                )
                
                # Set retention policy (30 days)
                self.logs.put_retention_policy(
                    logGroupName=log_group,
                    retentionInDays=30
                )
                
                created_groups.append(log_group)
                logger.info(f"Created log group: {log_group}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                    logger.info(f"Log group already exists: {log_group}")
                    created_groups.append(log_group)
                else:
                    logger.error(f"Failed to create log group {log_group}: {e}")
        
        return created_groups
    
    async def setup_complete_monitoring(self) -> Dict[str, Any]:
        """Setup complete CloudWatch monitoring infrastructure"""
        
        results = {
            'dashboard': None,
            'alarms': [],
            'log_groups': [],
            'errors': []
        }
        
        try:
            # Create dashboard
            dashboard_name = await self.create_health_dashboard()
            results['dashboard'] = dashboard_name
        except Exception as e:
            results['errors'].append(f"Dashboard creation failed: {e}")
        
        try:
            # Create alarms
            alarms = await self.create_health_alarms()
            results['alarms'] = alarms
        except Exception as e:
            results['errors'].append(f"Alarm creation failed: {e}")
        
        try:
            # Create log groups
            log_groups = await self.create_log_groups()
            results['log_groups'] = log_groups
        except Exception as e:
            results['errors'].append(f"Log group creation failed: {e}")
        
        return results


# Global CloudWatch integration instance
cloudwatch_integration = HealthCheckCloudWatchIntegration()


async def setup_cloudwatch_monitoring():
    """Setup complete CloudWatch monitoring"""
    return await cloudwatch_integration.setup_complete_monitoring()


async def send_health_metrics_to_cloudwatch(metrics: Dict[str, Any]):
    """Send health metrics to CloudWatch"""
    await cloudwatch_integration.send_health_metrics(metrics)
