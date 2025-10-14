"""
Deployment configuration for structured logging across environments.

Shows how to configure monitoring for:
- Development
- Staging  
- Production
- Docker deployments
- AWS Lambda deployments
"""

import os
from typing import Dict, Any
from packages.shared.monitoring.setup import MonitoringConfig, setup_service_monitoring
from packages.shared.monitoring import LogLevel


def get_development_config(service_name: str) -> MonitoringConfig:
    """Development environment configuration."""
    return MonitoringConfig(
        service_name=service_name,
        environment="development",
        
        # Logging - Console only for development
        log_level=LogLevel.DEBUG,
        use_cloudwatch_logs=False,
        
        # Metrics - In-memory for development
        use_cloudwatch_metrics=False,
        metrics_namespace=f"AI-Nutritionist-Dev",
        
        # Tracing - Console logging only
        use_xray=False,
        use_tracing_logs=True,
        
        # Health checks - Enabled with frequent checks
        enable_health_checks=True,
        health_check_interval=30,
        
        # AWS - Local region
        aws_region="us-east-1",
        
        # Extra tags
        extra_tags={
            "environment": "development",
            "version": "dev",
            "developer": os.getenv("USER", "unknown")
        }
    )


def get_staging_config(service_name: str) -> MonitoringConfig:
    """Staging environment configuration."""
    return MonitoringConfig(
        service_name=service_name,
        environment="staging",
        
        # Logging - CloudWatch with detailed logs
        log_level=LogLevel.INFO,
        use_cloudwatch_logs=True,
        cloudwatch_log_group=f"/ai-nutritionist/staging/{service_name}",
        cloudwatch_log_stream=f"{service_name}-staging-{os.getenv('INSTANCE_ID', 'default')}",
        
        # Metrics - CloudWatch with staging namespace
        use_cloudwatch_metrics=True,
        metrics_namespace="AI-Nutritionist-Staging",
        
        # Tracing - X-Ray with sampling
        use_xray=True,
        use_tracing_logs=True,
        
        # Health checks - Standard interval
        enable_health_checks=True,
        health_check_interval=60,
        
        # AWS - Staging region
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        
        # Extra tags
        extra_tags={
            "environment": "staging",
            "version": os.getenv("APP_VERSION", "unknown"),
            "build_id": os.getenv("BUILD_ID", "unknown"),
            "instance_id": os.getenv("INSTANCE_ID", "unknown")
        }
    )


def get_production_config(service_name: str) -> MonitoringConfig:
    """Production environment configuration."""
    return MonitoringConfig(
        service_name=service_name,
        environment="production",
        
        # Logging - CloudWatch with structured logs
        log_level=LogLevel.INFO,
        use_cloudwatch_logs=True,
        cloudwatch_log_group=f"/ai-nutritionist/production/{service_name}",
        cloudwatch_log_stream=f"{service_name}-{os.getenv('INSTANCE_ID', 'default')}",
        
        # Metrics - CloudWatch production namespace
        use_cloudwatch_metrics=True,
        metrics_namespace="AI-Nutritionist",
        
        # Tracing - X-Ray with optimized sampling
        use_xray=True,
        use_tracing_logs=False,  # Reduce log volume in production
        
        # Health checks - Standard interval
        enable_health_checks=True,
        health_check_interval=60,
        
        # AWS - Production region with multi-region support
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        
        # Extra tags
        extra_tags={
            "environment": "production",
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "build_id": os.getenv("BUILD_ID", "unknown"),
            "instance_id": os.getenv("INSTANCE_ID", "unknown"),
            "az": os.getenv("AWS_AVAILABILITY_ZONE", "unknown")
        }
    )


def get_lambda_config(service_name: str) -> MonitoringConfig:
    """AWS Lambda environment configuration."""
    return MonitoringConfig(
        service_name=service_name,
        environment=os.getenv("ENVIRONMENT", "production"),
        
        # Logging - Lambda logs go to CloudWatch automatically
        log_level=LogLevel.INFO,
        use_cloudwatch_logs=False,  # Lambda handles this
        
        # Metrics - CloudWatch with Lambda namespace
        use_cloudwatch_metrics=True,
        metrics_namespace="AI-Nutritionist/Lambda",
        
        # Tracing - X-Ray is native to Lambda
        use_xray=True,
        use_tracing_logs=False,
        
        # Health checks - Minimal for Lambda
        enable_health_checks=False,  # Lambda health is managed by AWS
        
        # AWS - Use Lambda environment
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        
        # Extra tags
        extra_tags={
            "environment": os.getenv("ENVIRONMENT", "production"),
            "version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION", "unknown"),
            "function_name": os.getenv("AWS_LAMBDA_FUNCTION_NAME", service_name),
            "memory_size": os.getenv("AWS_LAMBDA_FUNCTION_MEMORY_SIZE", "unknown")
        }
    )


def get_docker_config(service_name: str) -> MonitoringConfig:
    """Docker container environment configuration."""
    environment = os.getenv("ENVIRONMENT", "development")
    
    return MonitoringConfig(
        service_name=service_name,
        environment=environment,
        
        # Logging - CloudWatch for production, console for dev
        log_level=LogLevel.DEBUG if environment == "development" else LogLevel.INFO,
        use_cloudwatch_logs=environment != "development",
        cloudwatch_log_group=f"/ai-nutritionist/{environment}/{service_name}",
        cloudwatch_log_stream=f"{service_name}-{os.getenv('HOSTNAME', 'container')}",
        
        # Metrics - CloudWatch for production
        use_cloudwatch_metrics=environment != "development",
        metrics_namespace=f"AI-Nutritionist-{environment.title()}",
        
        # Tracing - X-Ray for production
        use_xray=environment == "production",
        use_tracing_logs=True,
        
        # Health checks - Always enabled in containers
        enable_health_checks=True,
        health_check_interval=60,
        
        # AWS - From environment
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        
        # Extra tags
        extra_tags={
            "environment": environment,
            "version": os.getenv("APP_VERSION", "unknown"),
            "container_id": os.getenv("HOSTNAME", "unknown"),
            "image_tag": os.getenv("IMAGE_TAG", "unknown")
        }
    )


# Configuration factory
ENVIRONMENT_CONFIGS = {
    "development": get_development_config,
    "staging": get_staging_config,
    "production": get_production_config,
    "lambda": get_lambda_config,
    "docker": get_docker_config
}


def setup_monitoring_for_environment(service_name: str, environment: str = None):
    """Setup monitoring based on environment."""
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    if environment not in ENVIRONMENT_CONFIGS:
        raise ValueError(f"Unknown environment: {environment}. Valid options: {list(ENVIRONMENT_CONFIGS.keys())}")
    
    config = ENVIRONMENT_CONFIGS[environment](service_name)
    return setup_service_monitoring(service_name, config)


# Docker Compose configuration
def create_docker_compose_monitoring():
    """Create docker-compose.yml configuration for monitoring stack."""
    return """
version: '3.8'

services:
  ai-nutritionist-api:
    build: .
    environment:
      - ENVIRONMENT=docker
      - SERVICE_NAME=ai-nutritionist-api
      - LOG_LEVEL=INFO
      - USE_CLOUDWATCH_LOGS=false
      - USE_CLOUDWATCH_METRICS=false
      - USE_XRAY=false
      - ENABLE_HEALTH_CHECKS=true
      - AWS_REGION=us-east-1
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    depends_on:
      - localstack
    networks:
      - monitoring

  # Local AWS services for development
  localstack:
    image: localstack/localstack:latest
    environment:
      - SERVICES=cloudwatch,logs,xray,s3,dynamodb
      - DEFAULT_REGION=us-east-1
      - DEBUG=1
    ports:
      - "4566:4566"
    volumes:
      - "/tmp/localstack:/tmp/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
    networks:
      - monitoring

  # Prometheus for metrics collection (alternative to CloudWatch)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - monitoring

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge

volumes:
  grafana_data:
"""


# Kubernetes configuration
def create_kubernetes_monitoring_config():
    """Create Kubernetes configuration for monitoring."""
    return """
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-nutritionist-monitoring-config
  namespace: ai-nutritionist
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  USE_CLOUDWATCH_LOGS: "true"
  USE_CLOUDWATCH_METRICS: "true"
  USE_XRAY: "true"
  ENABLE_HEALTH_CHECKS: "true"
  HEALTH_CHECK_INTERVAL: "60"
  AWS_REGION: "us-east-1"
  METRICS_NAMESPACE: "AI-Nutritionist"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-nutritionist-api
  namespace: ai-nutritionist
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-nutritionist-api
  template:
    metadata:
      labels:
        app: ai-nutritionist-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: ai-nutritionist-service-account
      containers:
      - name: api
        image: ai-nutritionist-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: ai-nutritionist-monitoring-config
        env:
        - name: SERVICE_NAME
          value: "ai-nutritionist-api"
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: ai-nutritionist-api-service
  namespace: ai-nutritionist
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: ai-nutritionist-api
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-nutritionist-service-account
  namespace: ai-nutritionist
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/ai-nutritionist-pod-role
"""


# Terraform configuration for AWS resources
def create_terraform_monitoring_config():
    """Create Terraform configuration for AWS monitoring resources."""
    return """
# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ai_nutritionist_api_application" {
  name              = "/ai-nutritionist/production/api/application"
  retention_in_days = 14
  
  tags = {
    Environment = "production"
    Service     = "ai-nutritionist-api"
    LogType     = "application"
  }
}

resource "aws_cloudwatch_log_group" "ai_nutritionist_api_error" {
  name              = "/ai-nutritionist/production/api/error"
  retention_in_days = 90
  
  tags = {
    Environment = "production"
    Service     = "ai-nutritionist-api"
    LogType     = "error"
  }
}

resource "aws_cloudwatch_log_group" "ai_nutritionist_api_audit" {
  name              = "/ai-nutritionist/production/api/audit"
  retention_in_days = 365
  
  tags = {
    Environment = "production"
    Service     = "ai-nutritionist-api"
    LogType     = "audit"
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "ai-nutritionist-api-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "api_errors_total"
  namespace           = "AI-Nutritionist"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors API error rate"
  
  dimensions = {
    service = "ai-nutritionist-api"
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_response_time" {
  alarm_name          = "ai-nutritionist-api-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "api_response_time_ms"
  namespace           = "AI-Nutritionist"
  period              = "300"
  statistic           = "Average"
  threshold           = "1000"
  alarm_description   = "This metric monitors API response time"
  
  dimensions = {
    service = "ai-nutritionist-api"
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "ai-nutritionist-alerts"
  
  tags = {
    Environment = "production"
    Service     = "ai-nutritionist"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "ai_nutritionist" {
  dashboard_name = "AI-Nutritionist-Production"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AI-Nutritionist", "api_requests_total", "service", "ai-nutritionist-api"],
            [".", "api_errors_total", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = "us-east-1"
          title  = "API Requests and Errors"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AI-Nutritionist", "api_response_time_ms", "service", "ai-nutritionist-api"]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "API Response Time"
        }
      }
    ]
  })
}

# X-Ray Tracing
resource "aws_xray_sampling_rule" "ai_nutritionist" {
  rule_name      = "ai-nutritionist-sampling-rule"
  priority       = 9000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.1
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "ai-nutritionist-*"
  resource_arn   = "*"
}

# IAM Role for monitoring
resource "aws_iam_role" "monitoring_role" {
  name = "ai-nutritionist-monitoring-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["ec2.amazonaws.com", "ecs-tasks.amazonaws.com", "lambda.amazonaws.com"]
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "monitoring_policy" {
  name = "ai-nutritionist-monitoring-policy"
  role = aws_iam_role.monitoring_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/ai-nutritionist/*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      }
    ]
  })
}
"""


# Example initialization script
def initialize_service_monitoring():
    """Initialize monitoring for a service based on environment."""
    service_name = os.getenv("SERVICE_NAME", "ai-nutritionist-api")
    environment = os.getenv("ENVIRONMENT", "development")
    
    print(f"Initializing monitoring for {service_name} in {environment} environment")
    
    try:
        monitoring = setup_monitoring_for_environment(service_name, environment)
        
        logger = monitoring.get_logger()
        logger.info(
            f"Monitoring initialized successfully",
            extra={
                "service_name": service_name,
                "environment": environment,
                "components": ["logging", "metrics", "tracing", "health"]
            }
        )
        
        # Add environment-specific health checks
        if environment in ["staging", "production", "docker"]:
            # Add database health check (example)
            # monitoring.add_database_health_check("database", db_connection_factory)
            
            # Add external API health checks
            monitoring.add_external_api_health_check(
                "openai_api",
                "https://api.openai.com/v1/models",
                timeout=5.0
            )
        
        return monitoring
        
    except Exception as e:
        print(f"Failed to initialize monitoring: {e}")
        raise


if __name__ == "__main__":
    # Initialize monitoring based on environment
    monitoring = initialize_service_monitoring()
    
    # Example usage
    logger = monitoring.get_logger()
    logger.info("Service started with monitoring enabled")
    
    # Print configuration files if requested
    if os.getenv("GENERATE_CONFIGS", "false").lower() == "true":
        print("=== Docker Compose Configuration ===")
        print(create_docker_compose_monitoring())
        
        print("\\n=== Kubernetes Configuration ===")
        print(create_kubernetes_monitoring_config())
        
        print("\\n=== Terraform Configuration ===")
        print(create_terraform_monitoring_config())
