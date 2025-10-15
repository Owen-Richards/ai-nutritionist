"""
Infrastructure Monitor

Monitors infrastructure metrics including CPU usage, memory usage,
network I/O, disk I/O with CloudWatch integration.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class InfrastructureMetrics:
    """Infrastructure monitoring metrics"""
    timestamp: datetime
    service_name: str
    instance_id: str
    cpu_utilization: float
    memory_utilization: float
    memory_used_bytes: int
    memory_total_bytes: int
    disk_read_bytes_per_sec: float
    disk_write_bytes_per_sec: float
    network_in_bytes_per_sec: float
    network_out_bytes_per_sec: float
    disk_usage_percent: float
    load_average: List[float]
    connection_count: int
    custom_metrics: Dict[str, float]


@dataclass
class AWSServiceMetrics:
    """AWS service-specific metrics"""
    service_type: str
    service_name: str
    timestamp: datetime
    metrics: Dict[str, Any]


class InfrastructureMonitor:
    """
    Comprehensive infrastructure monitoring with CloudWatch integration
    """
    
    def __init__(
        self,
        service_name: str = "ai-nutritionist",
        namespace: str = "AINutritionist/Infrastructure",
        region: str = "us-east-1",
        collect_interval: int = 30
    ):
        self.service_name = service_name
        self.namespace = namespace
        self.region = region
        self.collect_interval = collect_interval
        
        # AWS clients
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=region)
            self.ec2 = boto3.client('ec2', region_name=region)
            self.lambda_client = boto3.client('lambda', region_name=region)
            self.dynamodb = boto3.client('dynamodb', region_name=region)
            self.rds = boto3.client('rds', region_name=region)
            self.elasticache = boto3.client('elasticache', region_name=region)
        except Exception as e:
            logger.warning(f"Failed to initialize AWS clients: {e}")
            self.cloudwatch = None
        
        # Metrics storage
        self.infrastructure_metrics: List[InfrastructureMetrics] = []
        self.aws_service_metrics: List[AWSServiceMetrics] = []
        
        # System monitoring
        self.instance_id = self._get_instance_id()
        self.monitoring_enabled = True
        
        # Previous values for rate calculations
        self._prev_disk_stats = None
        self._prev_network_stats = None
        self._prev_timestamp = None
        
        # Start monitoring
        if self.monitoring_enabled:
            self._start_monitoring()
    
    def _get_instance_id(self) -> str:
        """Get EC2 instance ID or generate a unique identifier"""
        try:
            import urllib.request
            response = urllib.request.urlopen(
                'http://169.254.169.254/latest/meta-data/instance-id',
                timeout=2
            )
            return response.read().decode('utf-8')
        except Exception:
            # Fallback for non-EC2 environments
            import platform
            return f"{platform.node()}_{int(datetime.utcnow().timestamp())}"
    
    def _start_monitoring(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._collect_aws_metrics())
        asyncio.create_task(self._periodic_cleanup())
    
    async def _collect_system_metrics(self):
        """Collect system-level infrastructure metrics"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available for system metrics collection")
            return
        
        while self.monitoring_enabled:
            try:
                await asyncio.sleep(self.collect_interval)
                
                current_time = datetime.utcnow()
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                
                # Memory metrics
                memory = psutil.virtual_memory()
                
                # Disk metrics
                disk_usage = psutil.disk_usage('/')
                disk_io = psutil.disk_io_counters()
                
                # Network metrics
                network_io = psutil.net_io_counters()
                
                # Connection count
                try:
                    connections = len(psutil.net_connections())
                except (psutil.AccessDenied, AttributeError):
                    connections = 0
                
                # Calculate rates
                disk_read_rate = 0.0
                disk_write_rate = 0.0
                network_in_rate = 0.0
                network_out_rate = 0.0
                
                if self._prev_disk_stats and self._prev_network_stats and self._prev_timestamp:
                    time_delta = (current_time - self._prev_timestamp).total_seconds()
                    
                    if time_delta > 0:
                        disk_read_rate = (disk_io.read_bytes - self._prev_disk_stats.read_bytes) / time_delta
                        disk_write_rate = (disk_io.write_bytes - self._prev_disk_stats.write_bytes) / time_delta
                        network_in_rate = (network_io.bytes_recv - self._prev_network_stats.bytes_recv) / time_delta
                        network_out_rate = (network_io.bytes_sent - self._prev_network_stats.bytes_sent) / time_delta
                
                # Create metrics object
                metrics = InfrastructureMetrics(
                    timestamp=current_time,
                    service_name=self.service_name,
                    instance_id=self.instance_id,
                    cpu_utilization=cpu_percent,
                    memory_utilization=memory.percent,
                    memory_used_bytes=memory.used,
                    memory_total_bytes=memory.total,
                    disk_read_bytes_per_sec=disk_read_rate,
                    disk_write_bytes_per_sec=disk_write_rate,
                    network_in_bytes_per_sec=network_in_rate,
                    network_out_bytes_per_sec=network_out_rate,
                    disk_usage_percent=disk_usage.percent,
                    load_average=list(load_avg),
                    connection_count=connections,
                    custom_metrics={}
                )
                
                self.infrastructure_metrics.append(metrics)
                
                # Send to CloudWatch
                await self._send_infrastructure_metrics(metrics)
                
                # Update previous values
                self._prev_disk_stats = disk_io
                self._prev_network_stats = network_io
                self._prev_timestamp = current_time
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_aws_metrics(self):
        """Collect AWS service metrics"""
        while self.monitoring_enabled:
            try:
                await asyncio.sleep(120)  # Collect every 2 minutes
                
                # Collect Lambda metrics
                await self._collect_lambda_metrics()
                
                # Collect DynamoDB metrics
                await self._collect_dynamodb_metrics()
                
                # Collect RDS metrics (if applicable)
                await self._collect_rds_metrics()
                
                # Collect ElastiCache metrics (if applicable)
                await self._collect_elasticache_metrics()
                
            except Exception as e:
                logger.error(f"Error collecting AWS metrics: {e}")
    
    async def _collect_lambda_metrics(self):
        """Collect Lambda function metrics"""
        if not self.lambda_client:
            return
        
        try:
            # Get list of Lambda functions
            response = self.lambda_client.list_functions()
            
            for function in response.get('Functions', []):
                function_name = function['FunctionName']
                
                # Skip if not related to our service
                if self.service_name.lower() not in function_name.lower():
                    continue
                
                # Get function metrics from CloudWatch
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                
                # Duration metrics
                duration_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Duration',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average', 'Maximum']
                )
                
                # Error metrics
                error_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Errors',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                # Invocation metrics
                invocation_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                # Create metrics object
                lambda_metrics = AWSServiceMetrics(
                    service_type='lambda',
                    service_name=function_name,
                    timestamp=datetime.utcnow(),
                    metrics={
                        'duration': duration_response.get('Datapoints', []),
                        'errors': error_response.get('Datapoints', []),
                        'invocations': invocation_response.get('Datapoints', [])
                    }
                )
                
                self.aws_service_metrics.append(lambda_metrics)
                await self._send_lambda_metrics(lambda_metrics)
                
        except Exception as e:
            logger.warning(f"Failed to collect Lambda metrics: {e}")
    
    async def _collect_dynamodb_metrics(self):
        """Collect DynamoDB table metrics"""
        if not self.dynamodb:
            return
        
        try:
            # Get list of tables
            response = self.dynamodb.list_tables()
            
            for table_name in response.get('TableNames', []):
                # Skip if not related to our service
                if self.service_name.lower() not in table_name.lower():
                    continue
                
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                
                # Consumed capacity metrics
                read_capacity_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedReadCapacityUnits',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum', 'Average']
                )
                
                write_capacity_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedWriteCapacityUnits',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum', 'Average']
                )
                
                # Throttle metrics
                throttle_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ThrottledRequests',
                    Dimensions=[{'Name': 'TableName', 'Value': table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                dynamodb_metrics = AWSServiceMetrics(
                    service_type='dynamodb',
                    service_name=table_name,
                    timestamp=datetime.utcnow(),
                    metrics={
                        'read_capacity': read_capacity_response.get('Datapoints', []),
                        'write_capacity': write_capacity_response.get('Datapoints', []),
                        'throttles': throttle_response.get('Datapoints', [])
                    }
                )
                
                self.aws_service_metrics.append(dynamodb_metrics)
                await self._send_dynamodb_metrics(dynamodb_metrics)
                
        except Exception as e:
            logger.warning(f"Failed to collect DynamoDB metrics: {e}")
    
    async def _collect_rds_metrics(self):
        """Collect RDS metrics"""
        if not self.rds:
            return
        
        try:
            # Get RDS instances
            response = self.rds.describe_db_instances()
            
            for db_instance in response.get('DBInstances', []):
                instance_id = db_instance['DBInstanceIdentifier']
                
                # Skip if not related to our service
                if self.service_name.lower() not in instance_id.lower():
                    continue
                
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                
                # CPU utilization
                cpu_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average', 'Maximum']
                )
                
                # Database connections
                connections_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='DatabaseConnections',
                    Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average', 'Maximum']
                )
                
                rds_metrics = AWSServiceMetrics(
                    service_type='rds',
                    service_name=instance_id,
                    timestamp=datetime.utcnow(),
                    metrics={
                        'cpu_utilization': cpu_response.get('Datapoints', []),
                        'connections': connections_response.get('Datapoints', [])
                    }
                )
                
                self.aws_service_metrics.append(rds_metrics)
                await self._send_rds_metrics(rds_metrics)
                
        except Exception as e:
            logger.warning(f"Failed to collect RDS metrics: {e}")
    
    async def _collect_elasticache_metrics(self):
        """Collect ElastiCache metrics"""
        if not self.elasticache:
            return
        
        try:
            # Get ElastiCache clusters
            response = self.elasticache.describe_cache_clusters()
            
            for cluster in response.get('CacheClusters', []):
                cluster_id = cluster['CacheClusterId']
                
                # Skip if not related to our service
                if self.service_name.lower() not in cluster_id.lower():
                    continue
                
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                
                # CPU utilization
                cpu_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/ElastiCache',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'CacheClusterId', 'Value': cluster_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average', 'Maximum']
                )
                
                # Cache hit ratio
                hit_ratio_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/ElastiCache',
                    MetricName='CacheHitRate',
                    Dimensions=[{'Name': 'CacheClusterId', 'Value': cluster_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Average']
                )
                
                elasticache_metrics = AWSServiceMetrics(
                    service_type='elasticache',
                    service_name=cluster_id,
                    timestamp=datetime.utcnow(),
                    metrics={
                        'cpu_utilization': cpu_response.get('Datapoints', []),
                        'cache_hit_rate': hit_ratio_response.get('Datapoints', [])
                    }
                )
                
                self.aws_service_metrics.append(elasticache_metrics)
                await self._send_elasticache_metrics(elasticache_metrics)
                
        except Exception as e:
            logger.warning(f"Failed to collect ElastiCache metrics: {e}")
    
    async def _send_infrastructure_metrics(self, metrics: InfrastructureMetrics):
        """Send infrastructure metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'CPUUtilization',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.cpu_utilization,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'MemoryUtilization',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.memory_utilization,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'DiskUtilization',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.disk_usage_percent,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'DiskReadThroughput',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.disk_read_bytes_per_sec / (1024 * 1024),  # Convert to MB/s
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'DiskWriteThroughput',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.disk_write_bytes_per_sec / (1024 * 1024),  # Convert to MB/s
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'NetworkInThroughput',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.network_in_bytes_per_sec / (1024 * 1024),  # Convert to MB/s
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'NetworkOutThroughput',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.network_out_bytes_per_sec / (1024 * 1024),  # Convert to MB/s
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'ConnectionCount',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': metrics.connection_count,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            # Add load average metrics
            for i, load in enumerate(metrics.load_average):
                metric_data.append({
                    'MetricName': f'LoadAverage{i+1}min',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': metrics.service_name},
                        {'Name': 'InstanceId', 'Value': metrics.instance_id}
                    ],
                    'Value': load,
                    'Unit': 'None',
                    'Timestamp': metrics.timestamp
                })
            
            # Send metrics in batches
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
        except Exception as e:
            logger.warning(f"Failed to send infrastructure metrics to CloudWatch: {e}")
    
    async def _send_lambda_metrics(self, metrics: AWSServiceMetrics):
        """Send Lambda metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            # Process duration metrics
            for datapoint in metrics.metrics.get('duration', []):
                metric_data = [{
                    'MetricName': 'LambdaDurationAverage',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'FunctionName', 'Value': metrics.service_name}
                    ],
                    'Value': datapoint.get('Average', 0),
                    'Unit': 'Milliseconds',
                    'Timestamp': datapoint.get('Timestamp', datetime.utcnow())
                }]
                
                self.cloudwatch.put_metric_data(
                    Namespace=f"{self.namespace}/Lambda",
                    MetricData=metric_data
                )
                
        except Exception as e:
            logger.warning(f"Failed to send Lambda metrics to CloudWatch: {e}")
    
    async def _send_dynamodb_metrics(self, metrics: AWSServiceMetrics):
        """Send DynamoDB metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            # Process capacity metrics
            for datapoint in metrics.metrics.get('read_capacity', []):
                metric_data = [{
                    'MetricName': 'DynamoDBReadCapacity',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'TableName', 'Value': metrics.service_name}
                    ],
                    'Value': datapoint.get('Sum', 0),
                    'Unit': 'Count',
                    'Timestamp': datapoint.get('Timestamp', datetime.utcnow())
                }]
                
                self.cloudwatch.put_metric_data(
                    Namespace=f"{self.namespace}/DynamoDB",
                    MetricData=metric_data
                )
                
        except Exception as e:
            logger.warning(f"Failed to send DynamoDB metrics to CloudWatch: {e}")
    
    async def _send_rds_metrics(self, metrics: AWSServiceMetrics):
        """Send RDS metrics to CloudWatch"""
        # Similar implementation to other metric senders
        pass
    
    async def _send_elasticache_metrics(self, metrics: AWSServiceMetrics):
        """Send ElastiCache metrics to CloudWatch"""
        # Similar implementation to other metric senders
        pass
    
    async def _periodic_cleanup(self):
        """Periodically clean up old metrics"""
        while self.monitoring_enabled:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Clean up old metrics
                self.infrastructure_metrics = [
                    m for m in self.infrastructure_metrics 
                    if m.timestamp > cutoff_time
                ]
                self.aws_service_metrics = [
                    m for m in self.aws_service_metrics 
                    if m.timestamp > cutoff_time
                ]
                
                logger.debug("Cleaned up old infrastructure metrics")
                
            except Exception as e:
                logger.error(f"Error in infrastructure metrics cleanup: {e}")
    
    def get_infrastructure_summary(self) -> Dict[str, Any]:
        """Get infrastructure metrics summary"""
        if not self.infrastructure_metrics:
            return {'status': 'no_data'}
        
        # Get latest metrics
        latest_metrics = self.infrastructure_metrics[-1]
        
        # Calculate averages over last hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_metrics = [
            m for m in self.infrastructure_metrics 
            if m.timestamp > hour_ago
        ]
        
        if recent_metrics:
            avg_cpu = sum(m.cpu_utilization for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_utilization for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / len(recent_metrics)
            avg_connections = sum(m.connection_count for m in recent_metrics) / len(recent_metrics)
        else:
            avg_cpu = avg_memory = avg_disk = avg_connections = 0
        
        return {
            'timestamp': latest_metrics.timestamp.isoformat(),
            'service': self.service_name,
            'instance_id': latest_metrics.instance_id,
            'current_cpu_percent': latest_metrics.cpu_utilization,
            'current_memory_percent': latest_metrics.memory_utilization,
            'current_disk_percent': latest_metrics.disk_usage_percent,
            'current_connections': latest_metrics.connection_count,
            'avg_cpu_last_hour': avg_cpu,
            'avg_memory_last_hour': avg_memory,
            'avg_disk_last_hour': avg_disk,
            'avg_connections_last_hour': avg_connections,
            'memory_used_gb': latest_metrics.memory_used_bytes / (1024**3),
            'memory_total_gb': latest_metrics.memory_total_bytes / (1024**3),
            'load_average': latest_metrics.load_average,
            'disk_read_mb_per_sec': latest_metrics.disk_read_bytes_per_sec / (1024*1024),
            'disk_write_mb_per_sec': latest_metrics.disk_write_bytes_per_sec / (1024*1024),
            'network_in_mb_per_sec': latest_metrics.network_in_bytes_per_sec / (1024*1024),
            'network_out_mb_per_sec': latest_metrics.network_out_bytes_per_sec / (1024*1024)
        }
    
    def stop_monitoring(self):
        """Stop infrastructure monitoring"""
        self.monitoring_enabled = False


# Global infrastructure monitor
_infrastructure_monitor: Optional[InfrastructureMonitor] = None


def get_infrastructure_monitor(service_name: str = "ai-nutritionist") -> InfrastructureMonitor:
    """Get or create global infrastructure monitor"""
    global _infrastructure_monitor
    if _infrastructure_monitor is None:
        _infrastructure_monitor = InfrastructureMonitor(service_name)
    return _infrastructure_monitor


def setup_infrastructure_monitoring(service_name: str, **kwargs) -> InfrastructureMonitor:
    """Setup infrastructure monitoring"""
    global _infrastructure_monitor
    _infrastructure_monitor = InfrastructureMonitor(service_name, **kwargs)
    return _infrastructure_monitor
