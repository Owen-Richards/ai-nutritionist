"""
Distributed Tracing with X-Ray

Provides comprehensive distributed tracing capabilities using AWS X-Ray
for request tracing, service dependencies, bottleneck identification, and latency analysis.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class TraceSegment(NamedTuple):
    """Trace segment data structure"""
    id: str
    name: str
    start_time: float
    end_time: Optional[float]
    parent_id: Optional[str]
    annotations: Dict[str, Any]
    metadata: Dict[str, Any]
    error: Optional[Exception]
    http: Optional[Dict[str, Any]]


@dataclass
class ServiceDependency:
    """Service dependency information"""
    service_name: str
    operation: str
    call_count: int
    avg_response_time: float
    error_count: int
    error_rate: float


@dataclass
class BottleneckAnalysis:
    """Bottleneck analysis results"""
    operation: str
    avg_duration: float
    p95_duration: float
    p99_duration: float
    bottleneck_score: float
    contributing_factors: List[str]


class DistributedTracer:
    """
    Comprehensive distributed tracing system with AWS X-Ray integration
    """
    
    def __init__(
        self,
        service_name: str = "ai-nutritionist",
        region: str = "us-east-1",
        enable_xray: bool = True,
        sample_rate: float = 0.1
    ):
        self.service_name = service_name
        self.region = region
        self.enable_xray = enable_xray
        self.sample_rate = sample_rate
        
        # X-Ray configuration
        self.xray_recorder = None
        if enable_xray:
            try:
                from aws_xray_sdk.core import xray_recorder
                from aws_xray_sdk.core import patch_all
                
                # Configure X-Ray
                xray_recorder.configure(
                    service=service_name,
                    region=region,
                    sampling_rate=sample_rate
                )
                
                # Patch AWS SDK and common libraries
                patch_all()
                
                self.xray_recorder = xray_recorder
                logger.info(f"X-Ray tracing enabled for service: {service_name}")
                
            except ImportError:
                logger.warning("AWS X-Ray SDK not available")
                self.enable_xray = False
            except Exception as e:
                logger.warning(f"Failed to initialize X-Ray: {e}")
                self.enable_xray = False
        
        # Local trace storage
        self.trace_segments: List[TraceSegment] = []
        self.service_dependencies: Dict[str, ServiceDependency] = {}
        self.operation_metrics: Dict[str, List[float]] = {}
        
        # Active traces
        self.active_traces: Dict[str, Dict[str, Any]] = {}
        
        # Analysis results
        self.bottleneck_analysis: List[BottleneckAnalysis] = []
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background analysis tasks"""
        asyncio.create_task(self._periodic_analysis())
        asyncio.create_task(self._cleanup_old_traces())
    
    @asynccontextmanager
    async def trace_operation(
        self,
        operation: str,
        service: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        http_info: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing operations with comprehensive instrumentation
        """
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        service_name = service or self.service_name
        
        # Initialize trace data
        trace_data = {
            'trace_id': trace_id,
            'operation': operation,
            'service': service_name,
            'start_time': start_time,
            'annotations': annotations or {},
            'metadata': metadata or {},
            'http': http_info,
            'subsegments': [],
            'error': None
        }
        
        self.active_traces[trace_id] = trace_data
        
        # Start X-Ray segment
        xray_segment = None
        if self.xray_recorder and self.enable_xray:
            try:
                xray_segment = self.xray_recorder.begin_segment(
                    name=f"{service_name}::{operation}"
                )
                
                # Add annotations
                for key, value in (annotations or {}).items():
                    xray_segment.put_annotation(key, value)
                
                # Add metadata
                for key, value in (metadata or {}).items():
                    xray_segment.put_metadata(key, value)
                
                # Add HTTP information
                if http_info:
                    xray_segment.put_http_meta(**http_info)
                
            except Exception as e:
                logger.warning(f"Failed to start X-Ray segment: {e}")
        
        try:
            yield {
                'trace_id': trace_id,
                'start_time': start_time,
                'operation': operation,
                'service': service_name,
                'add_annotation': lambda k, v: self._add_annotation(trace_id, k, v),
                'add_metadata': lambda k, v: self._add_metadata(trace_id, k, v),
                'start_subsegment': lambda name: self._start_subsegment(trace_id, name)
            }
            
        except Exception as e:
            trace_data['error'] = e
            
            # Add error to X-Ray segment
            if xray_segment:
                try:
                    xray_segment.add_exception(e)
                except Exception:
                    pass
            
            raise
            
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # Complete trace data
            trace_data['end_time'] = end_time
            trace_data['duration'] = duration
            
            # Store trace segment
            segment = TraceSegment(
                id=trace_id,
                name=operation,
                start_time=start_time,
                end_time=end_time,
                parent_id=None,
                annotations=trace_data['annotations'],
                metadata=trace_data['metadata'],
                error=trace_data.get('error'),
                http=trace_data.get('http')
            )
            
            self.trace_segments.append(segment)
            
            # Update operation metrics
            if operation not in self.operation_metrics:
                self.operation_metrics[operation] = []
            self.operation_metrics[operation].append(duration * 1000)  # Convert to ms
            
            # Keep only recent metrics
            if len(self.operation_metrics[operation]) > 1000:
                self.operation_metrics[operation] = self.operation_metrics[operation][-500:]
            
            # End X-Ray segment
            if xray_segment:
                try:
                    xray_segment.put_metadata('duration_ms', duration * 1000)
                    xray_segment.put_metadata('success', trace_data.get('error') is None)
                    self.xray_recorder.end_segment()
                except Exception:
                    pass
            
            # Clean up active trace
            del self.active_traces[trace_id]
    
    @asynccontextmanager
    async def trace_dependency_call(
        self,
        service_name: str,
        operation: str,
        trace_id: Optional[str] = None,
        **kwargs
    ):
        """
        Trace calls to external dependencies
        """
        start_time = time.time()
        subsegment_id = str(uuid.uuid4())
        
        # Start X-Ray subsegment
        xray_subsegment = None
        if self.xray_recorder and self.enable_xray:
            try:
                xray_subsegment = self.xray_recorder.begin_subsegment(
                    name=f"{service_name}::{operation}"
                )
                xray_subsegment.put_annotation('service', service_name)
                xray_subsegment.put_annotation('operation', operation)
                
                # Add additional annotations
                for key, value in kwargs.items():
                    xray_subsegment.put_annotation(key, value)
                
            except Exception as e:
                logger.warning(f"Failed to start X-Ray subsegment: {e}")
        
        error_occurred = False
        
        try:
            yield {
                'subsegment_id': subsegment_id,
                'service': service_name,
                'operation': operation,
                'start_time': start_time
            }
            
        except Exception as e:
            error_occurred = True
            
            # Add error to X-Ray subsegment
            if xray_subsegment:
                try:
                    xray_subsegment.add_exception(e)
                except Exception:
                    pass
            
            raise
            
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # Update dependency metrics
            dep_key = f"{service_name}::{operation}"
            if dep_key not in self.service_dependencies:
                self.service_dependencies[dep_key] = ServiceDependency(
                    service_name=service_name,
                    operation=operation,
                    call_count=0,
                    avg_response_time=0.0,
                    error_count=0,
                    error_rate=0.0
                )
            
            dep = self.service_dependencies[dep_key]
            
            # Update metrics
            total_time = dep.avg_response_time * dep.call_count
            dep.call_count += 1
            dep.avg_response_time = (total_time + duration * 1000) / dep.call_count
            
            if error_occurred:
                dep.error_count += 1
            
            dep.error_rate = (dep.error_count / dep.call_count) * 100
            
            # End X-Ray subsegment
            if xray_subsegment:
                try:
                    xray_subsegment.put_metadata('duration_ms', duration * 1000)
                    xray_subsegment.put_metadata('success', not error_occurred)
                    self.xray_recorder.end_subsegment()
                except Exception:
                    pass
    
    def _add_annotation(self, trace_id: str, key: str, value: Any):
        """Add annotation to active trace"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id]['annotations'][key] = value
            
            # Add to X-Ray if available
            if self.xray_recorder and self.enable_xray:
                try:
                    self.xray_recorder.current_segment().put_annotation(key, value)
                except Exception:
                    pass
    
    def _add_metadata(self, trace_id: str, key: str, value: Any):
        """Add metadata to active trace"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id]['metadata'][key] = value
            
            # Add to X-Ray if available
            if self.xray_recorder and self.enable_xray:
                try:
                    self.xray_recorder.current_segment().put_metadata(key, value)
                except Exception:
                    pass
    
    def _start_subsegment(self, trace_id: str, name: str) -> str:
        """Start a subsegment within a trace"""
        subsegment_id = str(uuid.uuid4())
        
        if trace_id in self.active_traces:
            subsegment_data = {
                'id': subsegment_id,
                'name': name,
                'start_time': time.time(),
                'parent_trace': trace_id
            }
            self.active_traces[trace_id]['subsegments'].append(subsegment_data)
        
        return subsegment_id
    
    async def _periodic_analysis(self):
        """Periodically analyze traces for bottlenecks and patterns"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._analyze_bottlenecks()
                await self._analyze_service_dependencies()
            except Exception as e:
                logger.error(f"Error in periodic trace analysis: {e}")
    
    async def _analyze_bottlenecks(self):
        """Analyze operation performance to identify bottlenecks"""
        try:
            self.bottleneck_analysis.clear()
            
            for operation, durations in self.operation_metrics.items():
                if len(durations) < 10:  # Need minimum samples
                    continue
                
                # Calculate percentiles
                sorted_durations = sorted(durations)
                n = len(sorted_durations)
                
                avg_duration = sum(durations) / len(durations)
                p95_duration = sorted_durations[int(0.95 * n)]
                p99_duration = sorted_durations[int(0.99 * n)]
                
                # Calculate bottleneck score (higher = more problematic)
                # Factors: average duration, p95 variance, error rate
                duration_score = min(avg_duration / 1000, 10)  # Normalize to 0-10 scale
                variance_score = min((p95_duration - avg_duration) / avg_duration, 5)
                
                # Check for errors in recent traces
                recent_traces = [
                    t for t in self.trace_segments
                    if t.name == operation and 
                    (datetime.utcnow() - datetime.fromtimestamp(t.start_time)).total_seconds() < 3600
                ]
                
                error_rate = 0.0
                if recent_traces:
                    error_count = len([t for t in recent_traces if t.error])
                    error_rate = error_count / len(recent_traces)
                
                error_score = error_rate * 10
                
                bottleneck_score = duration_score + variance_score + error_score
                
                # Identify contributing factors
                contributing_factors = []
                if avg_duration > 2000:  # > 2 seconds
                    contributing_factors.append("High average response time")
                if variance_score > 2:
                    contributing_factors.append("High response time variance")
                if error_rate > 0.05:  # > 5%
                    contributing_factors.append("High error rate")
                if p99_duration > 10000:  # > 10 seconds
                    contributing_factors.append("Very slow worst-case performance")
                
                analysis = BottleneckAnalysis(
                    operation=operation,
                    avg_duration=avg_duration,
                    p95_duration=p95_duration,
                    p99_duration=p99_duration,
                    bottleneck_score=bottleneck_score,
                    contributing_factors=contributing_factors
                )
                
                self.bottleneck_analysis.append(analysis)
            
            # Sort by bottleneck score
            self.bottleneck_analysis.sort(key=lambda x: x.bottleneck_score, reverse=True)
            
        except Exception as e:
            logger.error(f"Error analyzing bottlenecks: {e}")
    
    async def _analyze_service_dependencies(self):
        """Analyze service dependencies for health and performance"""
        try:
            # Identify problematic dependencies
            problem_dependencies = []
            
            for dep_key, dep in self.service_dependencies.items():
                if dep.error_rate > 5.0:  # > 5% error rate
                    problem_dependencies.append({
                        'dependency': dep_key,
                        'issue': 'high_error_rate',
                        'value': dep.error_rate,
                        'impact': 'high' if dep.error_rate > 15 else 'medium'
                    })
                
                if dep.avg_response_time > 5000:  # > 5 seconds
                    problem_dependencies.append({
                        'dependency': dep_key,
                        'issue': 'slow_response',
                        'value': dep.avg_response_time,
                        'impact': 'high' if dep.avg_response_time > 10000 else 'medium'
                    })
            
            if problem_dependencies:
                logger.warning(f"Identified {len(problem_dependencies)} problematic dependencies")
                for problem in problem_dependencies:
                    logger.warning(
                        f"Dependency {problem['dependency']} has {problem['issue']}: "
                        f"{problem['value']:.2f} (impact: {problem['impact']})"
                    )
            
        except Exception as e:
            logger.error(f"Error analyzing service dependencies: {e}")
    
    async def _cleanup_old_traces(self):
        """Clean up old trace data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = time.time() - 86400  # 24 hours ago
                
                # Clean up old trace segments
                self.trace_segments = [
                    t for t in self.trace_segments
                    if t.start_time > cutoff_time
                ]
                
                # Clean up old operation metrics
                for operation in self.operation_metrics:
                    # Keep only last 500 measurements per operation
                    if len(self.operation_metrics[operation]) > 500:
                        self.operation_metrics[operation] = self.operation_metrics[operation][-500:]
                
                logger.debug("Cleaned up old trace data")
                
            except Exception as e:
                logger.error(f"Error cleaning up trace data: {e}")
    
    def get_trace_summary(self) -> Dict[str, Any]:
        """Get comprehensive trace analysis summary"""
        recent_time = time.time() - 3600  # Last hour
        
        recent_traces = [
            t for t in self.trace_segments
            if t.start_time > recent_time
        ]
        
        # Calculate overall metrics
        total_traces = len(recent_traces)
        error_traces = len([t for t in recent_traces if t.error])
        error_rate = (error_traces / total_traces * 100) if total_traces > 0 else 0
        
        # Calculate average response time
        if recent_traces:
            durations = [(t.end_time - t.start_time) * 1000 for t in recent_traces if t.end_time]
            avg_response_time = sum(durations) / len(durations) if durations else 0
        else:
            avg_response_time = 0
        
        # Top bottlenecks
        top_bottlenecks = self.bottleneck_analysis[:5]
        
        # Dependency health
        healthy_dependencies = len([
            d for d in self.service_dependencies.values()
            if d.error_rate < 5.0 and d.avg_response_time < 2000
        ])
        total_dependencies = len(self.service_dependencies)
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name,
            'tracing_enabled': self.enable_xray,
            'sample_rate': self.sample_rate,
            'traces_last_hour': total_traces,
            'error_rate_percent': error_rate,
            'avg_response_time_ms': avg_response_time,
            'active_traces': len(self.active_traces),
            'total_operations': len(self.operation_metrics),
            'top_bottlenecks': [
                {
                    'operation': b.operation,
                    'avg_duration_ms': b.avg_duration,
                    'bottleneck_score': b.bottleneck_score,
                    'factors': b.contributing_factors
                } for b in top_bottlenecks
            ],
            'service_dependencies': {
                'total': total_dependencies,
                'healthy': healthy_dependencies,
                'unhealthy': total_dependencies - healthy_dependencies,
                'details': [
                    {
                        'service': d.service_name,
                        'operation': d.operation,
                        'call_count': d.call_count,
                        'avg_response_time_ms': d.avg_response_time,
                        'error_rate_percent': d.error_rate
                    } for d in list(self.service_dependencies.values())[:10]
                ]
            }
        }
    
    def get_operation_latency_analysis(self, operation: str) -> Dict[str, Any]:
        """Get detailed latency analysis for a specific operation"""
        if operation not in self.operation_metrics:
            return {'error': 'Operation not found'}
        
        durations = self.operation_metrics[operation]
        if not durations:
            return {'error': 'No data available'}
        
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        return {
            'operation': operation,
            'sample_count': n,
            'avg_latency_ms': sum(durations) / n,
            'min_latency_ms': min(durations),
            'max_latency_ms': max(durations),
            'p50_latency_ms': sorted_durations[int(0.5 * n)],
            'p90_latency_ms': sorted_durations[int(0.9 * n)],
            'p95_latency_ms': sorted_durations[int(0.95 * n)],
            'p99_latency_ms': sorted_durations[int(0.99 * n)],
            'p999_latency_ms': sorted_durations[int(0.999 * n)] if n > 1000 else sorted_durations[-1]
        }


# Global distributed tracer
_distributed_tracer: Optional[DistributedTracer] = None


def get_distributed_tracer(service_name: str = "ai-nutritionist") -> DistributedTracer:
    """Get or create global distributed tracer"""
    global _distributed_tracer
    if _distributed_tracer is None:
        _distributed_tracer = DistributedTracer(service_name)
    return _distributed_tracer


def setup_distributed_tracing(service_name: str, **kwargs) -> DistributedTracer:
    """Setup distributed tracing"""
    global _distributed_tracer
    _distributed_tracer = DistributedTracer(service_name, **kwargs)
    return _distributed_tracer


# Convenience decorators
def trace_async(operation: str = None, service: str = None):
    """Decorator for async functions to add distributed tracing"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_distributed_tracer()
            op_name = operation or f"{func.__module__}.{func.__name__}"
            
            async with tracer.trace_operation(op_name, service=service):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_sync(operation: str = None, service: str = None):
    """Decorator for sync functions to add distributed tracing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_distributed_tracer()
            op_name = operation or f"{func.__module__}.{func.__name__}"
            
            # For sync functions, we'll use basic timing without async context
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record successful trace
                if tracer.xray_recorder and tracer.enable_xray:
                    try:
                        with tracer.xray_recorder.in_segment(op_name):
                            pass
                    except Exception:
                        pass
                
                return result
                
            except Exception as e:
                # Record error trace
                if tracer.xray_recorder and tracer.enable_xray:
                    try:
                        with tracer.xray_recorder.in_segment(op_name) as segment:
                            segment.add_exception(e)
                    except Exception:
                        pass
                
                raise
        
        return wrapper
    return decorator
