"""
Comprehensive Monitoring Service
Handles metrics collection, alerting, and incident response automation
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

import boto3
import requests
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics we collect"""
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    BUSINESS = "business"
    SECURITY = "security"
    COST = "cost"


@dataclass
class MetricData:
    """Structured metric data"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    dimensions: Dict[str, str]
    metric_type: MetricType
    namespace: str


@dataclass
class Alert:
    """Alert structure"""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    tags: Dict[str, str]


class ComprehensiveMonitoringService:
    """
    Advanced monitoring service with complete observability
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # AWS clients
        self.cloudwatch = boto3.client('cloudwatch')
        self.sns = boto3.client('sns')
        self.events = boto3.client('events')
        self.dynamodb = boto3.resource('dynamodb')
        self.ce = boto3.client('ce')  # Cost Explorer
        
        # Monitoring tables
        self.metrics_table = self.dynamodb.Table('ai-nutritionist-monitoring-metrics')
        self.alerts_table = self.dynamodb.Table('ai-nutritionist-monitoring-alerts')
        self.incidents_table = self.dynamodb.Table('ai-nutritionist-monitoring-incidents')
        
        # Configuration
        self.thresholds = self._load_thresholds()
        self.alert_endpoints = self._load_alert_endpoints()
        
        # Metric collectors
        self.metric_collectors = {
            MetricType.APPLICATION: self._collect_application_metrics,
            MetricType.INFRASTRUCTURE: self._collect_infrastructure_metrics,
            MetricType.BUSINESS: self._collect_business_metrics,
            MetricType.SECURITY: self._collect_security_metrics,
            MetricType.COST: self._collect_cost_metrics
        }
    
    def _load_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Load monitoring thresholds from configuration"""
        return {
            'error_rate': {'warning': 5.0, 'critical': 10.0},
            'response_time': {'warning': 3000, 'critical': 5000},
            'cpu_utilization': {'warning': 70.0, 'critical': 85.0},
            'memory_utilization': {'warning': 80.0, 'critical': 90.0},
            'disk_utilization': {'warning': 80.0, 'critical': 90.0},
            'lambda_duration': {'warning': 25000, 'critical': 28000},
            'dynamodb_throttles': {'warning': 1, 'critical': 5},
            'cost_anomaly': {'warning': 100.0, 'critical': 200.0},
            'revenue_drop': {'warning': 0.8, 'critical': 0.6},  # Ratio of expected
            'conversion_rate': {'warning': 0.02, 'critical': 0.01}
        }
    
    def _load_alert_endpoints(self) -> Dict[str, Dict[str, str]]:
        """Load alert endpoint configurations"""
        return {
            'sns_topics': {
                'technical': 'arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-alerts',
                'business': 'arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-business-alerts',
                'pagerduty': 'arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-pagerduty-alerts'
            },
            'webhooks': {
                'slack': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
                'discord': 'https://discord.com/api/webhooks/YOUR/WEBHOOK',
                'teams': 'https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK'
            },
            'pagerduty': {
                'integration_key': 'YOUR_PAGERDUTY_INTEGRATION_KEY',
                'api_url': 'https://events.pagerduty.com/v2/enqueue'
            }
        }
    
    async def collect_all_metrics(self) -> Dict[MetricType, List[MetricData]]:
        """Collect all types of metrics concurrently"""
        tasks = []
        
        for metric_type, collector in self.metric_collectors.items():
            task = asyncio.create_task(collector())
            tasks.append((metric_type, task))
        
        results = {}
        for metric_type, task in tasks:
            try:
                metrics = await task
                results[metric_type] = metrics
                logger.info(f"Collected {len(metrics)} {metric_type.value} metrics")
            except Exception as e:
                logger.error(f"Failed to collect {metric_type.value} metrics: {e}")
                results[metric_type] = []
        
        return results
    
    async def _collect_application_metrics(self) -> List[MetricData]:
        """Collect application performance metrics"""
        metrics = []
        now = datetime.utcnow()
        
        try:
            # Get Lambda metrics
            lambda_functions = [
                'ai-nutritionist-message-handler',
                'ai-nutritionist-billing-handler',
                'ai-nutritionist-scheduler-handler'
            ]
            
            for func_name in lambda_functions:
                # Duration metric
                duration_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[{'Name': 'FunctionName', 'Value': func_name}],
                    StartTime=now - timedelta(minutes=5),
                    EndTime=now,
                    Period=300,
                    Statistics=['Average']
                )
                
                if duration_response['Datapoints']:
                    latest = max(duration_response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics.append(MetricData(
                        name='LambdaDuration',
                        value=latest['Average'],
                        unit='Milliseconds',
                        timestamp=latest['Timestamp'],
                        dimensions={'FunctionName': func_name},
                        metric_type=MetricType.APPLICATION,
                        namespace='AI-Nutritionist/Application'
                    ))
                
                # Error metric
                error_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Errors',
                    Dimensions=[{'Name': 'FunctionName', 'Value': func_name}],
                    StartTime=now - timedelta(minutes=5),
                    EndTime=now,
                    Period=300,
                    Statistics=['Sum']
                )
                
                if error_response['Datapoints']:
                    latest = max(error_response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics.append(MetricData(
                        name='LambdaErrors',
                        value=latest['Sum'],
                        unit='Count',
                        timestamp=latest['Timestamp'],
                        dimensions={'FunctionName': func_name},
                        metric_type=MetricType.APPLICATION,
                        namespace='AI-Nutritionist/Application'
                    ))
            
            # Get API Gateway metrics
            api_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/ApiGateway',
                MetricName='Latency',
                Dimensions=[{'Name': 'ApiName', 'Value': 'ai-nutritionist-api'}],
                StartTime=now - timedelta(minutes=5),
                EndTime=now,
                Period=300,
                Statistics=['Average']
            )
            
            if api_response['Datapoints']:
                latest = max(api_response['Datapoints'], key=lambda x: x['Timestamp'])
                metrics.append(MetricData(
                    name='APILatency',
                    value=latest['Average'],
                    unit='Milliseconds',
                    timestamp=latest['Timestamp'],
                    dimensions={'ApiName': 'ai-nutritionist-api'},
                    metric_type=MetricType.APPLICATION,
                    namespace='AI-Nutritionist/Application'
                ))
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
        
        return metrics
    
    async def _collect_infrastructure_metrics(self) -> List[MetricData]:
        """Collect infrastructure metrics"""
        metrics = []
        now = datetime.utcnow()
        
        try:
            # DynamoDB metrics
            tables = [
                'ai-nutritionist-user-data',
                'ai-nutritionist-subscriptions',
                'ai-nutritionist-meal-plans'
            ]
            
            for table_name in tables:
                # Read capacity
                read_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedReadCapacityUnits',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=now - timedelta(minutes=5),
                    EndTime=now,
                    Period=300,
                    Statistics=['Sum']
                )
                
                if read_response['Datapoints']:
                    latest = max(read_response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics.append(MetricData(
                        name='DynamoDBReadCapacity',
                        value=latest['Sum'],
                        unit='Count',
                        timestamp=latest['Timestamp'],
                        dimensions={'TableName': table_name},
                        metric_type=MetricType.INFRASTRUCTURE,
                        namespace='AI-Nutritionist/Infrastructure'
                    ))
                
                # Throttles
                throttle_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='UserErrors',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=now - timedelta(minutes=5),
                    EndTime=now,
                    Period=300,
                    Statistics=['Sum']
                )
                
                if throttle_response['Datapoints']:
                    latest = max(throttle_response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics.append(MetricData(
                        name='DynamoDBThrottles',
                        value=latest['Sum'],
                        unit='Count',
                        timestamp=latest['Timestamp'],
                        dimensions={'TableName': table_name},
                        metric_type=MetricType.INFRASTRUCTURE,
                        namespace='AI-Nutritionist/Infrastructure'
                    ))
            
        except Exception as e:
            logger.error(f"Error collecting infrastructure metrics: {e}")
        
        return metrics
    
    async def _collect_business_metrics(self) -> List[MetricData]:
        """Collect business metrics"""
        metrics = []
        now = datetime.utcnow()
        
        try:
            # Query business events from logs
            logs_client = boto3.client('logs')
            
            # Revenue metrics
            revenue_query = """
            fields @timestamp, event, amount
            | filter event = "SUBSCRIPTION_EVENT"
            | stats sum(amount) as total_revenue by bin(5m)
            | sort @timestamp desc
            | limit 1
            """
            
            revenue_response = logs_client.start_query(
                logGroupName='/ai-nutritionist/application',
                startTime=int((now - timedelta(hours=1)).timestamp()),
                endTime=int(now.timestamp()),
                queryString=revenue_query
            )
            
            # Wait for query completion and get results
            query_id = revenue_response['queryId']
            await asyncio.sleep(2)  # Wait for query to complete
            
            results = logs_client.get_query_results(queryId=query_id)
            if results['results']:
                revenue = float(results['results'][0][1]['value'])
                metrics.append(MetricData(
                    name='Revenue',
                    value=revenue,
                    unit='None',
                    timestamp=now,
                    dimensions={'Period': '5minutes'},
                    metric_type=MetricType.BUSINESS,
                    namespace='AI-Nutritionist/Business'
                ))
            
            # User engagement metrics
            engagement_query = """
            fields @timestamp, event, user_id
            | filter event = "MEAL_PLAN_GENERATED"
            | stats count() as meal_plans by bin(5m)
            | sort @timestamp desc
            | limit 1
            """
            
            engagement_response = logs_client.start_query(
                logGroupName='/ai-nutritionist/application',
                startTime=int((now - timedelta(hours=1)).timestamp()),
                endTime=int(now.timestamp()),
                queryString=engagement_query
            )
            
            query_id = engagement_response['queryId']
            await asyncio.sleep(2)
            
            results = logs_client.get_query_results(queryId=query_id)
            if results['results']:
                meal_plans = float(results['results'][0][1]['value'])
                metrics.append(MetricData(
                    name='MealPlansGenerated',
                    value=meal_plans,
                    unit='Count',
                    timestamp=now,
                    dimensions={'Period': '5minutes'},
                    metric_type=MetricType.BUSINESS,
                    namespace='AI-Nutritionist/Business'
                ))
            
        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")
        
        return metrics
    
    async def _collect_security_metrics(self) -> List[MetricData]:
        """Collect security metrics"""
        metrics = []
        now = datetime.utcnow()
        
        try:
            # Query security events from logs
            logs_client = boto3.client('logs')
            
            security_query = """
            fields @timestamp, level, event, source_ip, user_id
            | filter level = "SECURITY" or event like /SECURITY/
            | stats count() as security_events by bin(5m)
            | sort @timestamp desc
            | limit 1
            """
            
            security_response = logs_client.start_query(
                logGroupName='/ai-nutritionist/security',
                startTime=int((now - timedelta(hours=1)).timestamp()),
                endTime=int(now.timestamp()),
                queryString=security_query
            )
            
            query_id = security_response['queryId']
            await asyncio.sleep(2)
            
            results = logs_client.get_query_results(queryId=query_id)
            if results['results']:
                security_events = float(results['results'][0][1]['value'])
                metrics.append(MetricData(
                    name='SecurityEvents',
                    value=security_events,
                    unit='Count',
                    timestamp=now,
                    dimensions={'Period': '5minutes'},
                    metric_type=MetricType.SECURITY,
                    namespace='AI-Nutritionist/Security'
                ))
            
        except Exception as e:
            logger.error(f"Error collecting security metrics: {e}")
        
        return metrics
    
    async def _collect_cost_metrics(self) -> List[MetricData]:
        """Collect cost metrics"""
        metrics = []
        now = datetime.utcnow()
        
        try:
            # Get cost data from Cost Explorer
            end_date = now.strftime('%Y-%m-%d')
            start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            
            cost_response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )
            
            # Process cost data
            total_cost = 0
            service_costs = {}
            
            for result in cost_response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    service_costs[service] = service_costs.get(service, 0) + cost
                    total_cost += cost
            
            metrics.append(MetricData(
                name='TotalCost',
                value=total_cost,
                unit='None',
                timestamp=now,
                dimensions={'Period': 'daily'},
                metric_type=MetricType.COST,
                namespace='AI-Nutritionist/Cost'
            ))
            
            for service, cost in service_costs.items():
                metrics.append(MetricData(
                    name='ServiceCost',
                    value=cost,
                    unit='None',
                    timestamp=now,
                    dimensions={'Service': service, 'Period': 'daily'},
                    metric_type=MetricType.COST,
                    namespace='AI-Nutritionist/Cost'
                ))
            
        except Exception as e:
            logger.error(f"Error collecting cost metrics: {e}")
        
        return metrics
    
    async def publish_metrics(self, metrics: List[MetricData]) -> bool:
        """Publish metrics to CloudWatch"""
        try:
            # Group metrics by namespace
            namespace_groups = {}
            for metric in metrics:
                namespace = metric.namespace
                if namespace not in namespace_groups:
                    namespace_groups[namespace] = []
                namespace_groups[namespace].append(metric)
            
            # Publish to CloudWatch in batches
            for namespace, metric_group in namespace_groups.items():
                metric_data = []
                
                for metric in metric_group:
                    metric_data.append({
                        'MetricName': metric.name,
                        'Value': metric.value,
                        'Unit': metric.unit,
                        'Timestamp': metric.timestamp,
                        'Dimensions': [
                            {'Name': k, 'Value': v} 
                            for k, v in metric.dimensions.items()
                        ]
                    })
                
                # CloudWatch has a limit of 20 metrics per request
                for i in range(0, len(metric_data), 20):
                    batch = metric_data[i:i+20]
                    self.cloudwatch.put_metric_data(
                        Namespace=namespace,
                        MetricData=batch
                    )
                
                logger.info(f"Published {len(metric_group)} metrics to {namespace}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing metrics: {e}")
            return False
    
    async def evaluate_alerts(self, metrics: List[MetricData]) -> List[Alert]:
        """Evaluate metrics against thresholds and generate alerts"""
        alerts = []
        
        for metric in metrics:
            threshold_config = self.thresholds.get(metric.name.lower())
            if not threshold_config:
                continue
            
            # Check critical threshold
            if metric.value >= threshold_config.get('critical', float('inf')):
                alert = Alert(
                    id=f"{metric.name}-{int(metric.timestamp.timestamp())}",
                    severity=AlertSeverity.CRITICAL,
                    title=f"Critical: {metric.name} exceeded threshold",
                    description=f"{metric.name} is {metric.value} {metric.unit}, above critical threshold of {threshold_config['critical']}",
                    metric_name=metric.name,
                    current_value=metric.value,
                    threshold=threshold_config['critical'],
                    timestamp=metric.timestamp,
                    tags=metric.dimensions
                )
                alerts.append(alert)
            
            # Check warning threshold
            elif metric.value >= threshold_config.get('warning', float('inf')):
                alert = Alert(
                    id=f"{metric.name}-{int(metric.timestamp.timestamp())}",
                    severity=AlertSeverity.HIGH,
                    title=f"Warning: {metric.name} exceeded threshold",
                    description=f"{metric.name} is {metric.value} {metric.unit}, above warning threshold of {threshold_config['warning']}",
                    metric_name=metric.name,
                    current_value=metric.value,
                    threshold=threshold_config['warning'],
                    timestamp=metric.timestamp,
                    tags=metric.dimensions
                )
                alerts.append(alert)
        
        return alerts
    
    async def send_alerts(self, alerts: List[Alert]) -> bool:
        """Send alerts through various channels"""
        try:
            for alert in alerts:
                # Send to appropriate SNS topic based on severity
                topic_arn = self._get_sns_topic_for_severity(alert.severity)
                
                message = {
                    'alert_id': alert.id,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'description': alert.description,
                    'metric_name': alert.metric_name,
                    'current_value': alert.current_value,
                    'threshold': alert.threshold,
                    'timestamp': alert.timestamp.isoformat(),
                    'tags': alert.tags
                }
                
                self.sns.publish(
                    TopicArn=topic_arn,
                    Message=json.dumps(message),
                    Subject=alert.title
                )
                
                # For critical alerts, also send to PagerDuty
                if alert.severity == AlertSeverity.CRITICAL:
                    await self._send_pagerduty_alert(alert)
                
                # Store alert in DynamoDB
                await self._store_alert(alert)
                
                logger.info(f"Sent {alert.severity.value} alert: {alert.title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
            return False
    
    def _get_sns_topic_for_severity(self, severity: AlertSeverity) -> str:
        """Get appropriate SNS topic based on alert severity"""
        if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            return self.alert_endpoints['sns_topics']['pagerduty']
        elif severity == AlertSeverity.MEDIUM:
            return self.alert_endpoints['sns_topics']['technical']
        else:
            return self.alert_endpoints['sns_topics']['technical']
    
    async def _send_pagerduty_alert(self, alert: Alert) -> bool:
        """Send alert to PagerDuty"""
        try:
            pagerduty_payload = {
                'routing_key': self.alert_endpoints['pagerduty']['integration_key'],
                'event_action': 'trigger',
                'dedup_key': alert.id,
                'payload': {
                    'summary': alert.title,
                    'source': 'AI-Nutritionist Monitoring',
                    'severity': alert.severity.value,
                    'component': alert.metric_name,
                    'custom_details': {
                        'description': alert.description,
                        'current_value': alert.current_value,
                        'threshold': alert.threshold,
                        'tags': alert.tags
                    }
                }
            }
            
            response = requests.post(
                self.alert_endpoints['pagerduty']['api_url'],
                json=pagerduty_payload,
                timeout=10
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {e}")
            return False
    
    async def _store_alert(self, alert: Alert) -> bool:
        """Store alert in DynamoDB for tracking"""
        try:
            self.alerts_table.put_item(
                Item={
                    'alert_id': alert.id,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'description': alert.description,
                    'metric_name': alert.metric_name,
                    'current_value': Decimal(str(alert.current_value)),
                    'threshold': Decimal(str(alert.threshold)),
                    'timestamp': alert.timestamp.isoformat(),
                    'tags': alert.tags,
                    'status': 'OPEN',
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
            return False
    
    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run a complete monitoring cycle"""
        start_time = time.time()
        results = {
            'cycle_start': datetime.utcnow().isoformat(),
            'metrics_collected': 0,
            'alerts_generated': 0,
            'alerts_sent': 0,
            'cycle_duration': 0,
            'success': False
        }
        
        try:
            logger.info("Starting monitoring cycle")
            
            # Collect all metrics
            all_metrics = await self.collect_all_metrics()
            
            # Flatten metrics list
            metrics_list = []
            for metric_type, metrics in all_metrics.items():
                metrics_list.extend(metrics)
            
            results['metrics_collected'] = len(metrics_list)
            
            # Publish metrics to CloudWatch
            await self.publish_metrics(metrics_list)
            
            # Evaluate alerts
            alerts = await self.evaluate_alerts(metrics_list)
            results['alerts_generated'] = len(alerts)
            
            # Send alerts if any
            if alerts:
                await self.send_alerts(alerts)
                results['alerts_sent'] = len(alerts)
            
            results['success'] = True
            logger.info(f"Monitoring cycle completed successfully: {len(metrics_list)} metrics, {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            results['error'] = str(e)
        
        finally:
            results['cycle_duration'] = time.time() - start_time
        
        return results


# Health Check Function for Scheduled Monitoring
async def lambda_handler(event, context):
    """Lambda handler for scheduled monitoring"""
    monitoring_service = ComprehensiveMonitoringService()
    
    try:
        # Run monitoring cycle
        results = await monitoring_service.run_monitoring_cycle()
        
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
        
    except Exception as e:
        logger.error(f"Error in monitoring lambda: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        service = ComprehensiveMonitoringService()
        results = await service.run_monitoring_cycle()
        print(json.dumps(results, indent=2))
    
    asyncio.run(main())
