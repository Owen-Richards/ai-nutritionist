"""
CloudWatch integration example for log aggregation and monitoring.

Demonstrates:
- CloudWatch Logs integration
- CloudWatch Metrics integration
- AWS X-Ray tracing
- Alert rules and dashboards
- Log retention policies
"""

import json
import time
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

from packages.shared.monitoring import (
    get_logger, get_tracer, get_business_metrics,
    LogLevel, EventType
)


class CloudWatchManager:
    """Manages CloudWatch integration for monitoring."""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.logger = get_logger()
        self.tracer = get_tracer()
        self._logs_client = None
        self._cloudwatch_client = None
        self._xray_client = None
    
    @property
    def logs_client(self):
        """Lazy initialization of CloudWatch Logs client."""
        if self._logs_client is None:
            self._logs_client = boto3.client('logs', region_name=self.region)
        return self._logs_client
    
    @property
    def cloudwatch_client(self):
        """Lazy initialization of CloudWatch client."""
        if self._cloudwatch_client is None:
            self._cloudwatch_client = boto3.client('cloudwatch', region_name=self.region)
        return self._cloudwatch_client
    
    @property
    def xray_client(self):
        """Lazy initialization of X-Ray client."""
        if self._xray_client is None:
            self._xray_client = boto3.client('xray', region_name=self.region)
        return self._xray_client
    
    def setup_log_groups(self, service_name: str) -> None:
        """Setup CloudWatch log groups with retention policies."""
        log_groups = [
            {
                "name": f"/aws/lambda/{service_name}-api",
                "retention_days": 30,
                "description": "API Gateway and Lambda function logs"
            },
            {
                "name": f"/ai-nutritionist/{service_name}/application",
                "retention_days": 14,
                "description": "Application logs"
            },
            {
                "name": f"/ai-nutritionist/{service_name}/error",
                "retention_days": 90,
                "description": "Error logs for debugging"
            },
            {
                "name": f"/ai-nutritionist/{service_name}/audit",
                "retention_days": 365,
                "description": "Audit logs for compliance"
            },
            {
                "name": f"/ai-nutritionist/{service_name}/security",
                "retention_days": 90,
                "description": "Security events"
            }
        ]
        
        for log_group in log_groups:
            self._create_log_group(log_group["name"], log_group["retention_days"])
            
            self.logger.info(
                "Log group configured",
                extra={
                    "log_group_name": log_group["name"],
                    "retention_days": log_group["retention_days"],
                    "description": log_group["description"]
                }
            )
    
    def _create_log_group(self, log_group_name: str, retention_days: int) -> None:
        """Create CloudWatch log group with retention policy."""
        try:
            # Create log group
            self.logs_client.create_log_group(logGroupName=log_group_name)
            
            # Set retention policy
            self.logs_client.put_retention_policy(
                logGroupName=log_group_name,
                retentionInDays=retention_days
            )
            
            self.logger.info(
                "Created CloudWatch log group",
                extra={
                    "log_group_name": log_group_name,
                    "retention_days": retention_days
                }
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                # Update retention policy for existing log group
                try:
                    self.logs_client.put_retention_policy(
                        logGroupName=log_group_name,
                        retentionInDays=retention_days
                    )
                    self.logger.info(
                        "Updated retention policy for existing log group",
                        extra={"log_group_name": log_group_name, "retention_days": retention_days}
                    )
                except Exception as update_error:
                    self.logger.error(
                        "Failed to update log group retention policy",
                        error=update_error,
                        extra={"log_group_name": log_group_name}
                    )
            else:
                self.logger.error(
                    "Failed to create log group",
                    error=e,
                    extra={"log_group_name": log_group_name}
                )
    
    def create_log_insights_queries(self, service_name: str) -> List[Dict[str, str]]:
        """Create useful CloudWatch Logs Insights queries."""
        queries = [
            {
                "name": "Error Analysis",
                "query": f"""
                    fields @timestamp, level, message, error.type, error.message
                    | filter level = "ERROR"
                    | stats count() by error.type
                    | sort count desc
                """,
                "log_group": f"/ai-nutritionist/{service_name}/application"
            },
            {
                "name": "API Performance",
                "query": f"""
                    fields @timestamp, context.operation, performance.duration_ms, response.status_code
                    | filter context.operation like /api/
                    | stats avg(performance.duration_ms), max(performance.duration_ms), count() by context.operation
                    | sort avg desc
                """,
                "log_group": f"/ai-nutritionist/{service_name}/application"
            },
            {
                "name": "User Activity",
                "query": f"""
                    fields @timestamp, business_event.entity_type, business_event.action, context.user_id
                    | filter business_event.event_type = "user_action"
                    | stats count() by business_event.action
                    | sort count desc
                """,
                "log_group": f"/ai-nutritionist/{service_name}/application"
            },
            {
                "name": "Database Performance",
                "query": f"""
                    fields @timestamp, extra.operation, extra.table, extra.duration_ms
                    | filter extra.operation in ["select", "insert", "update", "delete"]
                    | stats avg(extra.duration_ms), max(extra.duration_ms), count() by extra.table, extra.operation
                    | sort avg desc
                """,
                "log_group": f"/ai-nutritionist/{service_name}/application"
            },
            {
                "name": "Security Events",
                "query": f"""
                    fields @timestamp, business_event.action, business_event.metadata
                    | filter business_event.event_type = "security_event"
                    | sort @timestamp desc
                """,
                "log_group": f"/ai-nutritionist/{service_name}/security"
            },
            {
                "name": "Business KPI Trends",
                "query": f"""
                    fields @timestamp, extra.kpi_name, extra.value
                    | filter business_event.entity_type = "kpi"
                    | stats avg(extra.value) by extra.kpi_name, bin(5m)
                    | sort @timestamp desc
                """,
                "log_group": f"/ai-nutritionist/{service_name}/application"
            }
        ]
        
        self.logger.info(
            "Created CloudWatch Logs Insights queries",
            extra={
                "service_name": service_name,
                "queries_count": len(queries)
            }
        )
        
        return queries
    
    def create_cloudwatch_alarms(self, service_name: str) -> None:
        """Create CloudWatch alarms for monitoring."""
        alarms = [
            {
                "name": f"{service_name}-high-error-rate",
                "description": "Alert when error rate exceeds threshold",
                "metric_name": "api_errors_total",
                "namespace": "AI-Nutritionist",
                "statistic": "Sum",
                "period": 300,
                "evaluation_periods": 2,
                "threshold": 10,
                "comparison_operator": "GreaterThanThreshold"
            },
            {
                "name": f"{service_name}-high-response-time",
                "description": "Alert when API response time is high",
                "metric_name": "api_response_time_ms",
                "namespace": "AI-Nutritionist",
                "statistic": "Average",
                "period": 300,
                "evaluation_periods": 3,
                "threshold": 1000,
                "comparison_operator": "GreaterThanThreshold"
            },
            {
                "name": f"{service_name}-low-success-rate",
                "description": "Alert when API success rate is low",
                "metric_name": "api_requests_total",
                "namespace": "AI-Nutritionist",
                "statistic": "Average",
                "period": 300,
                "evaluation_periods": 2,
                "threshold": 0.95,
                "comparison_operator": "LessThanThreshold"
            },
            {
                "name": f"{service_name}-memory-usage-high",
                "description": "Alert when memory usage is high",
                "metric_name": "memory_usage_percent",
                "namespace": "AI-Nutritionist",
                "statistic": "Average",
                "period": 300,
                "evaluation_periods": 2,
                "threshold": 80,
                "comparison_operator": "GreaterThanThreshold"
            }
        ]
        
        for alarm in alarms:
            try:
                self.cloudwatch_client.put_metric_alarm(
                    AlarmName=alarm["name"],
                    AlarmDescription=alarm["description"],
                    MetricName=alarm["metric_name"],
                    Namespace=alarm["namespace"],
                    Statistic=alarm["statistic"],
                    Period=alarm["period"],
                    EvaluationPeriods=alarm["evaluation_periods"],
                    Threshold=alarm["threshold"],
                    ComparisonOperator=alarm["comparison_operator"],
                    TreatMissingData='notBreaching',
                    ActionsEnabled=True
                )
                
                self.logger.info(
                    "Created CloudWatch alarm",
                    extra={
                        "alarm_name": alarm["name"],
                        "metric_name": alarm["metric_name"],
                        "threshold": alarm["threshold"]
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to create CloudWatch alarm",
                    error=e,
                    extra={"alarm_name": alarm["name"]}
                )
    
    def create_cloudwatch_dashboard(self, service_name: str) -> str:
        """Create CloudWatch dashboard for monitoring."""
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AI-Nutritionist", "api_requests_total", "service", service_name],
                            [".", "api_errors_total", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "API Requests and Errors"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AI-Nutritionist", "api_response_time_ms", "service", service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "API Response Time"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AI-Nutritionist", "db_operations_total", "service", service_name, "operation", "select"],
                            ["...", "insert"],
                            ["...", "update"],
                            ["...", "delete"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Database Operations"
                    }
                },
                {
                    "type": "metric",
                    "x": 8,
                    "y": 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AI-Nutritionist", "external_api_calls_total", "service", service_name],
                            [".", "external_api_errors_total", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "External API Calls"
                    }
                },
                {
                    "type": "metric",
                    "x": 16,
                    "y": 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AI-Nutritionist", "memory_usage_percent", "service", service_name],
                            [".", "disk_usage_percent", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "System Resources"
                    }
                },
                {
                    "type": "log",
                    "x": 0,
                    "y": 12,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": f"SOURCE '/ai-nutritionist/{service_name}/application'\n| fields @timestamp, level, message\n| filter level = \"ERROR\"\n| sort @timestamp desc\n| limit 100",
                        "region": self.region,
                        "title": "Recent Errors",
                        "view": "table"
                    }
                }
            ]
        }
        
        dashboard_name = f"AI-Nutritionist-{service_name}"
        
        try:
            self.cloudwatch_client.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            self.logger.info(
                "Created CloudWatch dashboard",
                extra={
                    "dashboard_name": dashboard_name,
                    "widgets_count": len(dashboard_body["widgets"])
                }
            )
            
            # Log business event
            self.logger.business_event(
                event_type=EventType.SYSTEM_EVENT,
                entity_type="monitoring",
                action="dashboard_created",
                metadata={
                    "dashboard_name": dashboard_name,
                    "service_name": service_name
                }
            )
            
            return dashboard_name
            
        except Exception as e:
            self.logger.error(
                "Failed to create CloudWatch dashboard",
                error=e,
                extra={"dashboard_name": dashboard_name}
            )
            return ""
    
    def create_metric_filters(self, service_name: str) -> None:
        """Create CloudWatch metric filters to extract metrics from logs."""
        log_group = f"/ai-nutritionist/{service_name}/application"
        
        metric_filters = [
            {
                "filter_name": f"{service_name}-error-count",
                "filter_pattern": '[timestamp, request_id, level="ERROR", ...]',
                "metric_name": "application_errors_total",
                "metric_namespace": "AI-Nutritionist/Logs",
                "metric_value": "1",
                "default_value": 0
            },
            {
                "filter_name": f"{service_name}-api-response-time",
                "filter_pattern": '[timestamp, request_id, level, message="Request completed*", duration_ms]',
                "metric_name": "api_response_time_from_logs",
                "metric_namespace": "AI-Nutritionist/Logs",
                "metric_value": "$duration_ms",
                "default_value": 0
            },
            {
                "filter_name": f"{service_name}-business-events",
                "filter_pattern": '[timestamp, request_id, level, message, business_event="*"]',
                "metric_name": "business_events_total",
                "metric_namespace": "AI-Nutritionist/Logs",
                "metric_value": "1",
                "default_value": 0
            }
        ]
        
        for metric_filter in metric_filters:
            try:
                self.logs_client.put_metric_filter(
                    logGroupName=log_group,
                    filterName=metric_filter["filter_name"],
                    filterPattern=metric_filter["filter_pattern"],
                    metricTransformations=[
                        {
                            'metricName': metric_filter["metric_name"],
                            'metricNamespace': metric_filter["metric_namespace"],
                            'metricValue': metric_filter["metric_value"],
                            'defaultValue': metric_filter["default_value"]
                        }
                    ]
                )
                
                self.logger.info(
                    "Created CloudWatch metric filter",
                    extra={
                        "filter_name": metric_filter["filter_name"],
                        "log_group": log_group,
                        "metric_name": metric_filter["metric_name"]
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to create metric filter",
                    error=e,
                    extra={
                        "filter_name": metric_filter["filter_name"],
                        "log_group": log_group
                    }
                )
    
    def setup_xray_tracing(self, service_name: str) -> None:
        """Setup AWS X-Ray tracing configuration."""
        try:
            # Create X-Ray sampling rule
            sampling_rule = {
                "rule_name": f"{service_name}-sampling-rule",
                "priority": 9000,
                "fixed_rate": 0.1,  # Sample 10% of requests
                "reservoir_size": 1,
                "service_name": service_name,
                "service_type": "*",
                "host": "*",
                "method": "*",
                "url_path": "*",
                "version": 1
            }
            
            self.xray_client.create_sampling_rule(SamplingRule=sampling_rule)
            
            self.logger.info(
                "Created X-Ray sampling rule",
                extra={
                    "rule_name": sampling_rule["rule_name"],
                    "fixed_rate": sampling_rule["fixed_rate"],
                    "service_name": service_name
                }
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'RuleAlreadyExistsException':
                self.logger.info(
                    "X-Ray sampling rule already exists",
                    extra={"service_name": service_name}
                )
            else:
                self.logger.error(
                    "Failed to create X-Ray sampling rule",
                    error=e,
                    extra={"service_name": service_name}
                )
        except Exception as e:
            self.logger.error(
                "Failed to setup X-Ray tracing",
                error=e,
                extra={"service_name": service_name}
            )


def setup_complete_monitoring(service_name: str, region: str = "us-east-1") -> None:
    """Setup complete CloudWatch monitoring for a service."""
    logger = get_logger()
    
    logger.info(
        "Setting up complete CloudWatch monitoring",
        extra={
            "service_name": service_name,
            "region": region
        }
    )
    
    # Log business event
    logger.business_event(
        event_type=EventType.SYSTEM_EVENT,
        entity_type="monitoring",
        action="setup_started",
        metadata={
            "service_name": service_name,
            "region": region
        }
    )
    
    try:
        cloudwatch_manager = CloudWatchManager(region)
        
        # Setup log groups with retention policies
        cloudwatch_manager.setup_log_groups(service_name)
        
        # Create metric filters
        cloudwatch_manager.create_metric_filters(service_name)
        
        # Create CloudWatch alarms
        cloudwatch_manager.create_cloudwatch_alarms(service_name)
        
        # Create CloudWatch dashboard
        dashboard_name = cloudwatch_manager.create_cloudwatch_dashboard(service_name)
        
        # Setup X-Ray tracing
        cloudwatch_manager.setup_xray_tracing(service_name)
        
        # Create Log Insights queries
        queries = cloudwatch_manager.create_log_insights_queries(service_name)
        
        logger.info(
            "CloudWatch monitoring setup completed successfully",
            extra={
                "service_name": service_name,
                "dashboard_name": dashboard_name,
                "queries_count": len(queries)
            }
        )
        
        # Log successful completion
        logger.business_event(
            event_type=EventType.SYSTEM_EVENT,
            entity_type="monitoring",
            action="setup_completed",
            metadata={
                "service_name": service_name,
                "dashboard_name": dashboard_name,
                "components": ["log_groups", "metric_filters", "alarms", "dashboard", "xray"]
            }
        )
        
    except Exception as e:
        logger.error(
            "CloudWatch monitoring setup failed",
            error=e,
            extra={"service_name": service_name}
        )
        
        # Log failure event
        logger.business_event(
            event_type=EventType.ERROR_EVENT,
            entity_type="monitoring",
            action="setup_failed",
            metadata={
                "service_name": service_name,
                "error": str(e)
            },
            level=LogLevel.ERROR
        )
        
        raise


# Example usage
if __name__ == "__main__":
    from packages.shared.monitoring.setup import setup_service_monitoring
    
    # Setup monitoring first
    monitoring = setup_service_monitoring("ai-nutritionist-api")
    
    # Setup CloudWatch integration
    setup_complete_monitoring("ai-nutritionist-api", "us-east-1")
    
    logger = get_logger()
    logger.info("CloudWatch integration example completed")
