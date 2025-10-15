# Monitoring Configuration
monitoring_config = {
    # CloudWatch Log Groups
    "log_groups": {
        "application": "/ai-nutritionist/application",
        "performance": "/ai-nutritionist/performance", 
        "security": "/ai-nutritionist/security",
        "business": "/ai-nutritionist/business"
    },
    
    # Metric Thresholds
    "thresholds": {
        "error_rate": {
            "warning": 5.0,
            "critical": 10.0,
            "unit": "percent"
        },
        "response_time": {
            "warning": 3000,
            "critical": 5000,
            "unit": "milliseconds"
        },
        "lambda_duration": {
            "warning": 25000,
            "critical": 28000,
            "unit": "milliseconds"
        },
        "dynamodb_throttles": {
            "warning": 1,
            "critical": 5,
            "unit": "count"
        },
        "cpu_utilization": {
            "warning": 70.0,
            "critical": 85.0,
            "unit": "percent"
        },
        "memory_utilization": {
            "warning": 80.0,
            "critical": 90.0,
            "unit": "percent"
        },
        "revenue_drop": {
            "warning": 0.8,  # 20% drop
            "critical": 0.6,  # 40% drop
            "unit": "ratio"
        },
        "conversion_rate": {
            "warning": 0.02,  # 2%
            "critical": 0.01,  # 1%
            "unit": "ratio"
        }
    },
    
    # Alert Channels
    "alert_channels": {
        "sns_topics": {
            "technical": "arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-alerts",
            "business": "arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-business-alerts",
            "pagerduty": "arn:aws:sns:us-east-1:ACCOUNT:ai-nutritionist-pagerduty-alerts"
        },
        "slack": {
            "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
            "channels": {
                "alerts": "#alerts",
                "oncall": "#oncall",
                "business": "#business-metrics"
            }
        },
        "pagerduty": {
            "integration_key": "YOUR_PAGERDUTY_INTEGRATION_KEY",
            "api_url": "https://events.pagerduty.com/v2/enqueue"
        }
    },
    
    # Escalation Policies
    "escalation": {
        "severity_rules": {
            "sev1": {
                "response_time": 300,  # 5 minutes
                "escalation_time": 900,  # 15 minutes
                "channels": ["pagerduty", "phone", "slack"]
            },
            "sev2": {
                "response_time": 900,  # 15 minutes
                "escalation_time": 1800,  # 30 minutes
                "channels": ["pagerduty", "slack"]
            },
            "sev3": {
                "response_time": 3600,  # 1 hour
                "escalation_time": 7200,  # 2 hours
                "channels": ["slack", "email"]
            },
            "sev4": {
                "response_time": 14400,  # 4 hours
                "escalation_time": 28800,  # 8 hours
                "channels": ["email"]
            }
        },
        "teams": {
            "oncall-engineer": {
                "slack_channel": "#oncall",
                "pagerduty_service": "P1234567",
                "phone_numbers": ["+1234567890"]
            },
            "backend-team": {
                "slack_channel": "#backend",
                "email_list": "backend@ai-nutritionist.com"
            },
            "business-team": {
                "slack_channel": "#business",
                "email_list": "business@ai-nutritionist.com"
            },
            "platform-team": {
                "slack_channel": "#platform",
                "email_list": "platform@ai-nutritionist.com"
            }
        }
    },
    
    # Automated Response Actions
    "automated_responses": {
        "high_error_rate": {
            "actions": ["circuit_breaker", "scale_out", "alert_team"],
            "approvals_required": [],
            "rollback_procedure": [
                "Disable circuit breaker",
                "Scale back to normal capacity",
                "Monitor error rates"
            ]
        },
        "database_performance": {
            "actions": ["scale_out", "alert_team"],
            "approvals_required": ["database-lead"],
            "rollback_procedure": [
                "Revert capacity changes",
                "Check for data consistency"
            ]
        },
        "lambda_timeout": {
            "actions": ["restart_service", "alert_team"],
            "approvals_required": [],
            "rollback_procedure": [
                "Check lambda logs",
                "Verify function configuration"
            ]
        }
    },
    
    # Business Metrics
    "business_metrics": {
        "revenue": {
            "tracking_window": "1h",
            "anomaly_detection": True,
            "seasonality": "weekly"
        },
        "user_engagement": {
            "meal_plans_generated": {
                "threshold": 100,  # per hour
                "trend_analysis": True
            },
            "conversion_rate": {
                "baseline": 0.025,  # 2.5%
                "variance_threshold": 0.2  # 20%
            }
        }
    },
    
    # Dashboards
    "dashboards": {
        "main": {
            "name": "AI-Nutritionist-Main-Dashboard",
            "widgets": [
                "application_performance",
                "business_metrics",
                "lambda_functions",
                "dynamodb_performance",
                "cost_metrics"
            ]
        },
        "business": {
            "name": "AI-Nutritionist-Business-Dashboard", 
            "widgets": [
                "revenue_metrics",
                "user_engagement",
                "conversion_metrics",
                "product_usage",
                "customer_satisfaction"
            ]
        },
        "infrastructure": {
            "name": "AI-Nutritionist-Infrastructure-Dashboard",
            "widgets": [
                "api_gateway",
                "cloudfront",
                "rds_metrics",
                "lambda_performance"
            ]
        }
    },
    
    # Post-Mortem Configuration
    "post_mortem": {
        "auto_generate": {
            "sev1": True,
            "sev2": True,
            "sev3": False,
            "sev4": False
        },
        "required_reviewers": {
            "sev1": ["engineering-manager", "director", "cto"],
            "sev2": ["team-lead", "engineering-manager"],
            "sev3": ["team-lead"]
        },
        "sla_targets": {
            "detection_time": 300,  # 5 minutes
            "resolution_time": 3600,  # 1 hour for SEV1
            "postmortem_creation": 86400,  # 24 hours
            "action_item_completion": 604800  # 1 week
        }
    }
}

# Export configuration
import json

def get_monitoring_config():
    """Get monitoring configuration"""
    return monitoring_config

def save_config_to_file(filename="monitoring_config.json"):
    """Save configuration to JSON file"""
    with open(filename, 'w') as f:
        json.dump(monitoring_config, f, indent=2)

if __name__ == "__main__":
    save_config_to_file()
    print("Monitoring configuration saved to monitoring_config.json")
