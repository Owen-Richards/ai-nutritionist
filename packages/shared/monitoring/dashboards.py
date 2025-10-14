"""
Dashboard Manager

Creates and manages CloudWatch dashboards for comprehensive monitoring
with automated dashboard generation and customizable layouts.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DashboardManager:
    """
    Manages CloudWatch dashboards for comprehensive monitoring
    """
    
    def __init__(
        self,
        service_name: str = "ai-nutritionist",
        region: str = "us-east-1"
    ):
        self.service_name = service_name
        self.region = region
        
        # AWS client
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}")
            self.cloudwatch = None
        
        # Dashboard configurations
        self.dashboard_configs = {
            'performance': self._get_performance_dashboard_config(),
            'business': self._get_business_dashboard_config(),
            'infrastructure': self._get_infrastructure_dashboard_config(),
            'security': self._get_security_dashboard_config(),
            'overview': self._get_overview_dashboard_config()
        }
    
    async def create_all_dashboards(self) -> Dict[str, str]:
        """Create all monitoring dashboards"""
        dashboard_urls = {}
        
        for dashboard_type, config in self.dashboard_configs.items():
            try:
                dashboard_name = f"{self.service_name}-{dashboard_type}-monitoring"
                await self._create_dashboard(dashboard_name, config)
                dashboard_urls[dashboard_type] = self._get_dashboard_url(dashboard_name)
                logger.info(f"Created {dashboard_type} dashboard: {dashboard_name}")
            except Exception as e:
                logger.error(f"Failed to create {dashboard_type} dashboard: {e}")
        
        return dashboard_urls
    
    async def create_dashboard(
        self,
        dashboard_type: str,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a specific dashboard"""
        config = custom_config or self.dashboard_configs.get(dashboard_type)
        if not config:
            raise ValueError(f"Unknown dashboard type: {dashboard_type}")
        
        dashboard_name = f"{self.service_name}-{dashboard_type}-monitoring"
        await self._create_dashboard(dashboard_name, config)
        return self._get_dashboard_url(dashboard_name)
    
    async def _create_dashboard(self, name: str, config: Dict[str, Any]):
        """Create a CloudWatch dashboard"""
        if not self.cloudwatch:
            raise Exception("CloudWatch client not available")
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=name,
                DashboardBody=json.dumps(config)
            )
        except ClientError as e:
            raise Exception(f"Failed to create dashboard {name}: {e}")
    
    def _get_dashboard_url(self, dashboard_name: str) -> str:
        """Get the URL for a CloudWatch dashboard"""
        base_url = f"https://{self.region}.console.aws.amazon.com/cloudwatch/home"
        return f"{base_url}?region={self.region}#dashboards:name={dashboard_name}"
    
    def _get_performance_dashboard_config(self) -> Dict[str, Any]:
        """Get performance monitoring dashboard configuration"""
        return {
            "widgets": [
                # Response Times
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance", "ResponseTime", "Operation", "nutrition_analysis"],
                            [".", ".", ".", "meal_planning"],
                            [".", ".", ".", "user_registration"],
                            [".", ".", ".", "payment_processing"],
                            [".", ".", ".", "ai_coaching"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Average Response Times by Operation",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries",
                        "stacked": False
                    }
                },
                
                # Throughput
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance", "RequestsPerSecond", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Requests Per Second",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Error Rates
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance", "ErrorRatePercent", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Error Rate Percentage",
                        "yAxis": {"left": {"min": 0, "max": 100}},
                        "view": "timeSeries"
                    }
                },
                
                # Response Time Percentiles
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance/Aggregated", "ResponseTimeP50", "Service", self.service_name],
                            [".", "ResponseTimeP90", ".", "."],
                            [".", "ResponseTimeP95", ".", "."],
                            [".", "ResponseTimeP99", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Response Time Percentiles",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Concurrent Requests
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance", "ConcurrentRequests", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Concurrent Requests",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Operation Success Rate
                {
                    "type": "metric",
                    "x": 12, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance", "SuccessRate", "Operation", "nutrition_analysis"],
                            [".", ".", ".", "meal_planning"],
                            [".", ".", ".", "user_registration"],
                            [".", ".", ".", "payment_processing"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Operation Success Rates",
                        "yAxis": {"left": {"min": 0, "max": 1}},
                        "view": "timeSeries"
                    }
                }
            ]
        }
    
    def _get_business_dashboard_config(self) -> Dict[str, Any]:
        """Get business metrics dashboard configuration"""
        return {
            "widgets": [
                # Active Users
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Aggregated", "ActiveUsers"],
                            [".", "DailyActiveUsers"]
                        ],
                        "period": 300,
                        "stat": "Maximum",
                        "region": self.region,
                        "title": "Active Users",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Revenue
                {
                    "type": "metric",
                    "x": 8, "y": 0, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Revenue", "Revenue", "SubscriptionType", "premium"],
                            [".", ".", ".", "basic"],
                            [".", ".", ".", "enterprise"]
                        ],
                        "period": 3600,  # 1 hour
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Revenue by Subscription Type",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries",
                        "stacked": True
                    }
                },
                
                # Feature Usage
                {
                    "type": "metric",
                    "x": 16, "y": 0, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Features", "FeatureUsage", "FeatureName", "nutrition_tracking"],
                            [".", ".", ".", "meal_planning"],
                            [".", ".", ".", "workout_tracking"],
                            [".", ".", ".", "ai_coaching"],
                            [".", ".", ".", "progress_analysis"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Feature Usage",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # User Engagement
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Engagement", "UserEngagement", "Action", "login"],
                            [".", ".", ".", "food_logging"],
                            [".", ".", ".", "goal_setting"],
                            [".", ".", ".", "report_viewing"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "User Engagement by Action",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Conversion Funnel
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Conversions", "ConversionEvent", "FunnelStage", "registration"],
                            [".", ".", ".", "trial_start"],
                            [".", ".", ".", "first_goal"],
                            [".", ".", ".", "subscription"],
                            [".", ".", ".", "retention_30d"]
                        ],
                        "period": 3600,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Conversion Funnel",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Session Duration
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Aggregated", "AverageSessionDuration"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Average Session Duration",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # User Satisfaction
                {
                    "type": "metric",
                    "x": 12, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Features", "UserSatisfaction", "FeatureName", "nutrition_tracking"],
                            [".", ".", ".", "meal_planning"],
                            [".", ".", ".", "ai_coaching"]
                        ],
                        "period": 3600,
                        "stat": "Average",
                        "region": self.region,
                        "title": "User Satisfaction by Feature",
                        "yAxis": {"left": {"min": 0, "max": 5}},
                        "view": "timeSeries"
                    }
                }
            ]
        }
    
    def _get_infrastructure_dashboard_config(self) -> Dict[str, Any]:
        """Get infrastructure monitoring dashboard configuration"""
        return {
            "widgets": [
                # CPU Utilization
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Infrastructure", "CPUUtilization", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "CPU Utilization",
                        "yAxis": {"left": {"min": 0, "max": 100}},
                        "view": "timeSeries"
                    }
                },
                
                # Memory Utilization
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Infrastructure", "MemoryUtilization", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Memory Utilization",
                        "yAxis": {"left": {"min": 0, "max": 100}},
                        "view": "timeSeries"
                    }
                },
                
                # Disk I/O
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Infrastructure", "DiskReadThroughput", "Service", self.service_name],
                            [".", "DiskWriteThroughput", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Disk I/O Throughput",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Network I/O
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Infrastructure", "NetworkInThroughput", "Service", self.service_name],
                            [".", "NetworkOutThroughput", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Network I/O Throughput",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Lambda Performance
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Duration", "FunctionName", f"{self.service_name}-nutrition-handler"],
                            [".", ".", ".", f"{self.service_name}-payment-handler"],
                            [".", ".", ".", f"{self.service_name}-message-handler"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Lambda Function Duration",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # DynamoDB Performance
                {
                    "type": "metric",
                    "x": 8, "y": 12, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", f"{self.service_name}-user-data"],
                            [".", "ConsumedWriteCapacityUnits", ".", "."],
                            [".", "ConsumedReadCapacityUnits", "TableName", f"{self.service_name}-nutrition-data"],
                            [".", "ConsumedWriteCapacityUnits", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "DynamoDB Capacity Usage",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Connection Count
                {
                    "type": "metric",
                    "x": 16, "y": 12, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Infrastructure", "ConnectionCount", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Connection Count",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                }
            ]
        }
    
    def _get_security_dashboard_config(self) -> Dict[str, Any]:
        """Get security monitoring dashboard configuration"""
        return {
            "widgets": [
                # API Gateway 4XX Errors
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/ApiGateway", "4XXError", "ApiName", f"{self.service_name}-api"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "API Gateway 4XX Errors",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Failed Authentication Attempts
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Security", "AuthenticationFailures", "Type", "invalid_token"],
                            [".", ".", ".", "expired_token"],
                            [".", ".", ".", "malformed_request"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Authentication Failures",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # WAF Blocked Requests
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/WAFV2", "BlockedRequests", "WebACL", f"{self.service_name}-protection"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "WAF Blocked Requests",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Rate Limiting
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Security", "RateLimitExceeded", "Source", "api"],
                            [".", ".", ".", "sms"],
                            [".", ".", ".", "email"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Rate Limit Violations",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                }
            ]
        }
    
    def _get_overview_dashboard_config(self) -> Dict[str, Any]:
        """Get high-level overview dashboard configuration"""
        return {
            "widgets": [
                # System Health Score
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 6, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/HealthCheck", "SystemHealthScore"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "System Health Score",
                        "yAxis": {"left": {"min": 0, "max": 100}},
                        "view": "singleValue"
                    }
                },
                
                # Current Active Users
                {
                    "type": "metric",
                    "x": 6, "y": 0, "width": 6, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Aggregated", "ActiveUsers"]
                        ],
                        "period": 300,
                        "stat": "Maximum",
                        "region": self.region,
                        "title": "Current Active Users",
                        "yAxis": {"left": {"min": 0}},
                        "view": "singleValue"
                    }
                },
                
                # Daily Revenue
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 6, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Aggregated", "DailyRevenue"]
                        ],
                        "period": 86400,  # 1 day
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Daily Revenue",
                        "yAxis": {"left": {"min": 0}},
                        "view": "singleValue"
                    }
                },
                
                # Error Rate
                {
                    "type": "metric",
                    "x": 18, "y": 0, "width": 6, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance/Aggregated", "ErrorRatePercent", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Error Rate %",
                        "yAxis": {"left": {"min": 0, "max": 100}},
                        "view": "singleValue"
                    }
                },
                
                # Service Performance Trend
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Performance/Aggregated", "AverageResponseTime", "Service", self.service_name],
                            ["AINutritionist/Performance", "RequestsPerSecond", "Service", self.service_name]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": self.region,
                        "title": "Performance Trend (Last 24 Hours)",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                },
                
                # Top Features by Usage
                {
                    "type": "metric",
                    "x": 12, "y": 6, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["AINutritionist/Business/Aggregated", "TopFeatureUsage", "FeatureName", "nutrition_tracking"],
                            [".", ".", ".", "meal_planning"],
                            [".", ".", ".", "ai_coaching"],
                            [".", ".", ".", "workout_tracking"],
                            [".", ".", ".", "progress_analysis"]
                        ],
                        "period": 3600,
                        "stat": "Sum",
                        "region": self.region,
                        "title": "Top Features by Usage",
                        "yAxis": {"left": {"min": 0}},
                        "view": "timeSeries"
                    }
                }
            ]
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary of available dashboards"""
        return {
            'service': self.service_name,
            'region': self.region,
            'available_dashboards': list(self.dashboard_configs.keys()),
            'dashboard_urls': {
                dashboard_type: self._get_dashboard_url(f"{self.service_name}-{dashboard_type}-monitoring")
                for dashboard_type in self.dashboard_configs.keys()
            }
        }


# Global dashboard manager
_dashboard_manager: Optional[DashboardManager] = None


def get_dashboard_manager(service_name: str = "ai-nutritionist") -> DashboardManager:
    """Get or create global dashboard manager"""
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager(service_name)
    return _dashboard_manager


def setup_dashboard_management(service_name: str, **kwargs) -> DashboardManager:
    """Setup dashboard management"""
    global _dashboard_manager
    _dashboard_manager = DashboardManager(service_name, **kwargs)
    return _dashboard_manager
