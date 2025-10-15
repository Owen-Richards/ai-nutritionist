"""
Comprehensive Performance Monitor

Main entry point for application performance monitoring with CloudWatch and X-Ray integration.
Tracks response times, throughput, error rates, and resource utilization.
"""

import asyncio
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Application performance metrics"""
    operation: str
    timestamp: datetime
    response_time: float  # milliseconds
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThroughputMetrics:
    """Throughput and volume metrics"""
    operation: str
    timestamp: datetime
    requests_per_second: float
    concurrent_requests: int
    queue_size: int
    total_requests: int


@dataclass
class ResourceMetrics:
    """Resource utilization metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_in_mb: float
    network_io_out_mb: float


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system with CloudWatch integration
    """
    
    def __init__(
        self,
        service_name: str,
        namespace: str = "AINutritionist/Performance",
        region: str = "us-east-1",
        enable_xray: bool = True
    ):
        self.service_name = service_name
        self.namespace = namespace
        self.region = region
        self.enable_xray = enable_xray
        
        # AWS clients
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=region)
            if enable_xray:
                from aws_xray_sdk.core import xray_recorder
                self.xray = xray_recorder
        except Exception as e:
            logger.warning(f"Failed to initialize AWS clients: {e}")
            self.cloudwatch = None
            self.xray = None
        
        # Metrics storage
        self.performance_metrics: List[PerformanceMetrics] = []
        self.throughput_metrics: List[ThroughputMetrics] = []
        self.resource_metrics: List[ResourceMetrics] = []
        
        # Real-time counters
        self.active_requests = 0
        self.total_requests = 0
        self.error_count = 0
        self.response_times: List[float] = []
        
        # Configuration
        self.max_metrics_buffer = 1000
        self.flush_interval = 60  # seconds
        self.percentiles = [50, 90, 95, 99]
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._periodic_flush())
        asyncio.create_task(self._collect_system_metrics())
    
    @asynccontextmanager
    async def trace_operation(self, operation: str, **attributes):
        """Context manager for tracing operations with performance monitoring"""
        start_time = time.time()
        self.active_requests += 1
        self.total_requests += 1
        
        request_id = attributes.get('request_id', f"{operation}_{int(start_time * 1000)}")
        success = True
        error_type = None
        error_message = None
        
        # Start X-Ray subsegment if enabled
        subsegment = None
        if self.xray and self.enable_xray:
            try:
                subsegment = self.xray.begin_subsegment(operation)
                subsegment.put_annotation('service', self.service_name)
                for key, value in attributes.items():
                    subsegment.put_annotation(key, value)
            except Exception as e:
                logger.warning(f"Failed to start X-Ray subsegment: {e}")
        
        try:
            yield {
                'request_id': request_id,
                'start_time': start_time,
                'operation': operation
            }
        except Exception as e:
            success = False
            error_type = type(e).__name__
            error_message = str(e)
            self.error_count += 1
            
            # Add error to X-Ray subsegment
            if subsegment:
                try:
                    subsegment.add_exception(e)
                except Exception:
                    pass
            
            raise
        finally:
            # Calculate response time
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            self.response_times.append(response_time)
            
            # Keep only recent response times for percentile calculations
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-500:]
            
            self.active_requests -= 1
            
            # End X-Ray subsegment
            if subsegment:
                try:
                    subsegment.put_metadata('response_time_ms', response_time)
                    subsegment.put_metadata('success', success)
                    self.xray.end_subsegment()
                except Exception:
                    pass
            
            # Store performance metrics
            metrics = PerformanceMetrics(
                operation=operation,
                timestamp=datetime.utcnow(),
                response_time=response_time,
                success=success,
                error_type=error_type,
                error_message=error_message,
                request_id=request_id,
                custom_attributes=attributes
            )
            
            self.performance_metrics.append(metrics)
            
            # Send real-time metrics to CloudWatch
            await self._send_realtime_metrics(metrics)
    
    async def track_throughput(self, operation: str):
        """Track throughput metrics for an operation"""
        current_time = datetime.utcnow()
        
        # Calculate requests per second over the last minute
        recent_metrics = [
            m for m in self.performance_metrics
            if m.operation == operation and 
            (current_time - m.timestamp).total_seconds() <= 60
        ]
        
        requests_per_second = len(recent_metrics) / 60.0
        
        throughput = ThroughputMetrics(
            operation=operation,
            timestamp=current_time,
            requests_per_second=requests_per_second,
            concurrent_requests=self.active_requests,
            queue_size=0,  # Would need to be provided by caller
            total_requests=len([m for m in self.performance_metrics if m.operation == operation])
        )
        
        self.throughput_metrics.append(throughput)
        await self._send_throughput_metrics(throughput)
    
    async def track_resource_usage(self, cpu_percent: float, memory_usage: Dict[str, float], 
                                 io_stats: Dict[str, float]):
        """Track resource utilization metrics"""
        metrics = ResourceMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory_usage.get('percent', 0),
            memory_used_mb=memory_usage.get('used_mb', 0),
            memory_total_mb=memory_usage.get('total_mb', 0),
            disk_io_read_mb=io_stats.get('disk_read_mb', 0),
            disk_io_write_mb=io_stats.get('disk_write_mb', 0),
            network_io_in_mb=io_stats.get('network_in_mb', 0),
            network_io_out_mb=io_stats.get('network_out_mb', 0)
        )
        
        self.resource_metrics.append(metrics)
        await self._send_resource_metrics(metrics)
    
    async def _send_realtime_metrics(self, metrics: PerformanceMetrics):
        """Send real-time metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'ResponseTime',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'Operation', 'Value': metrics.operation}
                    ],
                    'Value': metrics.response_time,
                    'Unit': 'Milliseconds',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'RequestCount',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'Operation', 'Value': metrics.operation}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'ErrorRate',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'Operation', 'Value': metrics.operation}
                    ],
                    'Value': 0 if metrics.success else 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            # Add error type dimension if there was an error
            if not metrics.success and metrics.error_type:
                metric_data.append({
                    'MetricName': 'ErrorsByType',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'Operation', 'Value': metrics.operation},
                        {'Name': 'ErrorType', 'Value': metrics.error_type}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                })
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send metrics to CloudWatch: {e}")
    
    async def _send_throughput_metrics(self, metrics: ThroughputMetrics):
        """Send throughput metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'RequestsPerSecond',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name},
                        {'Name': 'Operation', 'Value': metrics.operation}
                    ],
                    'Value': metrics.requests_per_second,
                    'Unit': 'Count/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'ConcurrentRequests',
                    'Dimensions': [
                        {'Name': 'Service', 'Value': self.service_name}
                    ],
                    'Value': metrics.concurrent_requests,
                    'Unit': 'Count',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send throughput metrics to CloudWatch: {e}")
    
    async def _send_resource_metrics(self, metrics: ResourceMetrics):
        """Send resource metrics to CloudWatch"""
        if not self.cloudwatch:
            return
        
        try:
            metric_data = [
                {
                    'MetricName': 'CPUUtilization',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.cpu_percent,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'MemoryUtilization',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.memory_percent,
                    'Unit': 'Percent',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'MemoryUsed',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.memory_used_mb,
                    'Unit': 'Megabytes',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'DiskReadThroughput',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.disk_io_read_mb,
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'DiskWriteThroughput',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.disk_io_write_mb,
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'NetworkInThroughput',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.network_io_in_mb,
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                },
                {
                    'MetricName': 'NetworkOutThroughput',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': metrics.network_io_out_mb,
                    'Unit': 'Megabytes/Second',
                    'Timestamp': metrics.timestamp
                }
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send resource metrics to CloudWatch: {e}")
    
    async def _periodic_flush(self):
        """Periodically flush aggregated metrics"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_aggregated_metrics()
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _flush_aggregated_metrics(self):
        """Flush aggregated performance metrics"""
        if not self.cloudwatch or not self.response_times:
            return
        
        try:
            # Calculate percentiles
            sorted_times = sorted(self.response_times)
            percentile_values = {}
            
            for p in self.percentiles:
                index = int((p / 100.0) * len(sorted_times))
                if index >= len(sorted_times):
                    index = len(sorted_times) - 1
                percentile_values[p] = sorted_times[index]
            
            # Calculate error rate
            recent_metrics = [
                m for m in self.performance_metrics
                if (datetime.utcnow() - m.timestamp).total_seconds() <= self.flush_interval
            ]
            
            total_requests = len(recent_metrics)
            error_requests = len([m for m in recent_metrics if not m.success])
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Send aggregated metrics
            metric_data = [
                {
                    'MetricName': 'AverageResponseTime',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': statistics.mean(self.response_times),
                    'Unit': 'Milliseconds'
                },
                {
                    'MetricName': 'ErrorRatePercent',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': error_rate,
                    'Unit': 'Percent'
                }
            ]
            
            # Add percentile metrics
            for p, value in percentile_values.items():
                metric_data.append({
                    'MetricName': f'ResponseTimeP{p}',
                    'Dimensions': [{'Name': 'Service', 'Value': self.service_name}],
                    'Value': value,
                    'Unit': 'Milliseconds'
                })
            
            self.cloudwatch.put_metric_data(
                Namespace=f"{self.namespace}/Aggregated",
                MetricData=metric_data
            )
            
        except Exception as e:
            logger.error(f"Failed to flush aggregated metrics: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available for system metrics collection")
            return
        
        while True:
            try:
                await asyncio.sleep(30)  # Collect every 30 seconds
                
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()
                
                # Track previous values for rate calculation
                if not hasattr(self, '_prev_disk_io'):
                    self._prev_disk_io = disk_io
                    self._prev_network_io = network_io
                    self._prev_time = time.time()
                    continue
                
                current_time = time.time()
                time_delta = current_time - self._prev_time
                
                # Calculate rates (bytes per second -> MB per second)
                disk_read_rate = ((disk_io.read_bytes - self._prev_disk_io.read_bytes) / time_delta) / (1024 * 1024)
                disk_write_rate = ((disk_io.write_bytes - self._prev_disk_io.write_bytes) / time_delta) / (1024 * 1024)
                network_in_rate = ((network_io.bytes_recv - self._prev_network_io.bytes_recv) / time_delta) / (1024 * 1024)
                network_out_rate = ((network_io.bytes_sent - self._prev_network_io.bytes_sent) / time_delta) / (1024 * 1024)
                
                await self.track_resource_usage(
                    cpu_percent=cpu_percent,
                    memory_usage={
                        'percent': memory.percent,
                        'used_mb': memory.used / (1024 * 1024),
                        'total_mb': memory.total / (1024 * 1024)
                    },
                    io_stats={
                        'disk_read_mb': max(0, disk_read_rate),
                        'disk_write_mb': max(0, disk_write_rate),
                        'network_in_mb': max(0, network_in_rate),
                        'network_out_mb': max(0, network_out_rate)
                    }
                )
                
                # Update previous values
                self._prev_disk_io = disk_io
                self._prev_network_io = network_io
                self._prev_time = current_time
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the current period"""
        if not self.response_times:
            return {'status': 'no_data'}
        
        recent_metrics = [
            m for m in self.performance_metrics
            if (datetime.utcnow() - m.timestamp).total_seconds() <= 300  # Last 5 minutes
        ]
        
        total_requests = len(recent_metrics)
        error_requests = len([m for m in recent_metrics if not m.success])
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name,
            'active_requests': self.active_requests,
            'total_requests': self.total_requests,
            'avg_response_time_ms': statistics.mean(self.response_times),
            'min_response_time_ms': min(self.response_times),
            'max_response_time_ms': max(self.response_times),
            'error_rate_percent': (error_requests / total_requests * 100) if total_requests > 0 else 0,
            'requests_last_5min': total_requests,
            'errors_last_5min': error_requests,
            'p50_response_time_ms': statistics.median(self.response_times),
            'p95_response_time_ms': self._calculate_percentile(self.response_times, 95),
            'p99_response_time_ms': self._calculate_percentile(self.response_times, 99)
        }
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(service_name: str = "ai-nutritionist") -> PerformanceMonitor:
    """Get or create global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(service_name)
    return _performance_monitor


def setup_performance_monitoring(service_name: str, **kwargs) -> PerformanceMonitor:
    """Setup performance monitoring for a service"""
    global _performance_monitor
    _performance_monitor = PerformanceMonitor(service_name, **kwargs)
    return _performance_monitor
