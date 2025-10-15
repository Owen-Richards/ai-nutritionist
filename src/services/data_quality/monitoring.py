"""
Data Quality Monitoring and Analytics

Data quality metrics, anomaly detection, data lineage tracking,
and quality dashboards.
"""

import json
import statistics
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import logging

from .validators import ValidationResult

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of data quality metrics."""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"
    INTEGRITY = "integrity"


class AlertSeverity(Enum):
    """Severity levels for data quality alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DataQualityMetric:
    """Represents a data quality metric."""
    name: str
    metric_type: MetricType
    value: float
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_within_threshold(self) -> bool:
        """Check if metric value is within acceptable thresholds."""
        if self.threshold_min is not None and self.value < self.threshold_min:
            return False
        if self.threshold_max is not None and self.value > self.threshold_max:
            return False
        return True
    
    @property
    def severity(self) -> AlertSeverity:
        """Calculate alert severity based on threshold violation."""
        if self.is_within_threshold:
            return AlertSeverity.LOW
        
        if self.threshold_min is not None and self.value < self.threshold_min:
            violation_percent = (self.threshold_min - self.value) / self.threshold_min
        elif self.threshold_max is not None and self.value > self.threshold_max:
            violation_percent = (self.value - self.threshold_max) / self.threshold_max
        else:
            violation_percent = 0
        
        if violation_percent > 0.5:
            return AlertSeverity.CRITICAL
        elif violation_percent > 0.2:
            return AlertSeverity.HIGH
        else:
            return AlertSeverity.MEDIUM


@dataclass
class DataQualityAlert:
    """Represents a data quality alert."""
    metric_name: str
    message: str
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataQualityMetrics:
    """Calculates and tracks data quality metrics."""
    
    def __init__(self):
        self.metrics_history = defaultdict(list)
        self.metric_calculators = {}
        self.thresholds = {}
        self.alerts = []
        self._register_default_calculators()
    
    def _register_default_calculators(self):
        """Register default metric calculators."""
        self.metric_calculators.update({
            'completeness': self._calculate_completeness,
            'accuracy': self._calculate_accuracy,
            'consistency': self._calculate_consistency,
            'timeliness': self._calculate_timeliness,
            'validity': self._calculate_validity,
            'uniqueness': self._calculate_uniqueness,
            'integrity': self._calculate_integrity
        })
    
    def register_metric_calculator(self, name: str, calculator: Callable):
        """Register a custom metric calculator."""
        self.metric_calculators[name] = calculator
    
    def set_threshold(self, metric_name: str, min_threshold: Optional[float] = None,
                     max_threshold: Optional[float] = None):
        """Set quality thresholds for a metric."""
        self.thresholds[metric_name] = {
            'min': min_threshold,
            'max': max_threshold
        }
    
    def calculate_metric(self, metric_name: str, data: Any, **kwargs) -> DataQualityMetric:
        """Calculate a specific data quality metric."""
        if metric_name not in self.metric_calculators:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        calculator = self.metric_calculators[metric_name]
        value = calculator(data, **kwargs)
        
        thresholds = self.thresholds.get(metric_name, {})
        
        metric = DataQualityMetric(
            name=metric_name,
            metric_type=MetricType(metric_name) if metric_name in [m.value for m in MetricType] else MetricType.ACCURACY,
            value=value,
            threshold_min=thresholds.get('min'),
            threshold_max=thresholds.get('max'),
            metadata=kwargs
        )
        
        # Store in history
        self.metrics_history[metric_name].append(metric)
        
        # Check for alerts
        if not metric.is_within_threshold:
            alert = DataQualityAlert(
                metric_name=metric_name,
                message=f"Metric '{metric_name}' value {value} violates threshold",
                severity=metric.severity,
                metadata={'metric': metric}
            )
            self.alerts.append(alert)
        
        return metric
    
    def _calculate_completeness(self, data: List[Dict[str, Any]], fields: List[str] = None, **kwargs) -> float:
        """Calculate data completeness percentage."""
        if not data:
            return 0.0
        
        if fields is None:
            # Calculate overall completeness
            total_fields = 0
            complete_fields = 0
            
            for record in data:
                for key, value in record.items():
                    total_fields += 1
                    if value is not None and value != "" and value != []:
                        complete_fields += 1
            
            return (complete_fields / total_fields) * 100 if total_fields > 0 else 0.0
        
        else:
            # Calculate completeness for specific fields
            total_checks = len(data) * len(fields)
            complete_checks = 0
            
            for record in data:
                for field in fields:
                    if field in record and record[field] is not None and record[field] != "":
                        complete_checks += 1
            
            return (complete_checks / total_checks) * 100 if total_checks > 0 else 0.0
    
    def _calculate_accuracy(self, data: List[Dict[str, Any]], 
                          validation_rules: Dict[str, Callable] = None, **kwargs) -> float:
        """Calculate data accuracy percentage."""
        if not data or not validation_rules:
            return 100.0  # Assume accurate if no rules to check
        
        total_checks = 0
        accurate_checks = 0
        
        for record in data:
            for field, rule in validation_rules.items():
                if field in record:
                    total_checks += 1
                    try:
                        if rule(record[field]):
                            accurate_checks += 1
                    except Exception:
                        pass  # Rule failed, don't count as accurate
        
        return (accurate_checks / total_checks) * 100 if total_checks > 0 else 100.0
    
    def _calculate_consistency(self, data: List[Dict[str, Any]], 
                             consistency_fields: List[str] = None, **kwargs) -> float:
        """Calculate data consistency percentage."""
        if not data or not consistency_fields:
            return 100.0
        
        consistency_violations = 0
        total_comparisons = 0
        
        # Check internal consistency within records
        for record in data:
            for field in consistency_fields:
                if field in record:
                    # Example: check if related fields are consistent
                    if field == 'email' and 'user_id' in record:
                        # Could check if email domain matches expected pattern for user type
                        total_comparisons += 1
                        # Simplified consistency check
                        if '@' in str(record[field]):
                            pass  # Consistent
                        else:
                            consistency_violations += 1
        
        if total_comparisons == 0:
            return 100.0
        
        return ((total_comparisons - consistency_violations) / total_comparisons) * 100
    
    def _calculate_timeliness(self, data: List[Dict[str, Any]], 
                            timestamp_field: str = 'created_at',
                            max_age_hours: float = 24, **kwargs) -> float:
        """Calculate data timeliness percentage."""
        if not data:
            return 100.0
        
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(hours=max_age_hours)
        
        timely_records = 0
        
        for record in data:
            if timestamp_field in record:
                try:
                    timestamp = record[timestamp_field]
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    
                    if timestamp >= cutoff_time:
                        timely_records += 1
                except Exception:
                    pass  # Skip invalid timestamps
        
        return (timely_records / len(data)) * 100
    
    def _calculate_validity(self, data: List[Dict[str, Any]], 
                          format_rules: Dict[str, str] = None, **kwargs) -> float:
        """Calculate data format validity percentage."""
        if not data or not format_rules:
            return 100.0
        
        from .validators import DataTypeValidator
        validator = DataTypeValidator()
        
        total_checks = 0
        valid_checks = 0
        
        for record in data:
            for field, format_type in format_rules.items():
                if field in record:
                    total_checks += 1
                    result = validator.validate_field_type(record[field], format_type)
                    if result.is_valid:
                        valid_checks += 1
        
        return (valid_checks / total_checks) * 100 if total_checks > 0 else 100.0
    
    def _calculate_uniqueness(self, data: List[Dict[str, Any]], 
                            unique_fields: List[str] = None, **kwargs) -> float:
        """Calculate data uniqueness percentage."""
        if not data or not unique_fields:
            return 100.0
        
        total_uniqueness_score = 0
        
        for field in unique_fields:
            values = []
            for record in data:
                if field in record and record[field] is not None:
                    values.append(record[field])
            
            if values:
                unique_values = len(set(values))
                total_values = len(values)
                field_uniqueness = (unique_values / total_values) * 100
                total_uniqueness_score += field_uniqueness
        
        return total_uniqueness_score / len(unique_fields) if unique_fields else 100.0
    
    def _calculate_integrity(self, data: List[Dict[str, Any]], 
                           relationships: Dict[str, str] = None, **kwargs) -> float:
        """Calculate referential integrity percentage."""
        if not data or not relationships:
            return 100.0
        
        # This would integrate with referential integrity validator
        # For now, return a placeholder
        return 95.0  # Simplified implementation
    
    def get_metric_history(self, metric_name: str, 
                          time_window: Optional[timedelta] = None) -> List[DataQualityMetric]:
        """Get historical metrics for a specific metric."""
        history = self.metrics_history.get(metric_name, [])
        
        if time_window is None:
            return history
        
        cutoff_time = datetime.utcnow() - time_window
        return [metric for metric in history if metric.timestamp >= cutoff_time]
    
    def get_metric_trend(self, metric_name: str, 
                        time_window: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """Calculate trend for a metric over time."""
        history = self.get_metric_history(metric_name, time_window)
        
        if len(history) < 2:
            return {'trend': 'insufficient_data', 'change': 0}
        
        values = [metric.value for metric in history]
        timestamps = [metric.timestamp for metric in history]
        
        # Simple linear trend calculation
        first_value = values[0]
        last_value = values[-1]
        change = last_value - first_value
        
        trend = 'stable'
        if change > 1:
            trend = 'improving'
        elif change < -1:
            trend = 'declining'
        
        return {
            'trend': trend,
            'change': change,
            'average': statistics.mean(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'sample_count': len(values),
            'time_span': (timestamps[-1] - timestamps[0]).total_seconds() / 3600  # hours
        }


class AnomalyDetector:
    """Detects anomalies in data quality metrics and data patterns."""
    
    def __init__(self):
        self.baseline_models = {}
        self.anomaly_threshold = 2.0  # Standard deviations
        self.detection_rules = []
    
    def train_baseline(self, metric_name: str, historical_values: List[float]):
        """Train baseline model for anomaly detection."""
        if len(historical_values) < 10:
            logger.warning(f"Insufficient data for baseline training: {metric_name}")
            return
        
        mean_value = statistics.mean(historical_values)
        std_value = statistics.stdev(historical_values)
        
        self.baseline_models[metric_name] = {
            'mean': mean_value,
            'std': std_value,
            'min': min(historical_values),
            'max': max(historical_values),
            'training_samples': len(historical_values)
        }
    
    def detect_statistical_anomaly(self, metric_name: str, value: float) -> Dict[str, Any]:
        """Detect statistical anomalies using baseline model."""
        if metric_name not in self.baseline_models:
            return {'is_anomaly': False, 'reason': 'no_baseline_model'}
        
        baseline = self.baseline_models[metric_name]
        mean = baseline['mean']
        std = baseline['std']
        
        if std == 0:
            return {'is_anomaly': False, 'reason': 'zero_variance'}
        
        z_score = abs(value - mean) / std
        is_anomaly = z_score > self.anomaly_threshold
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'threshold': self.anomaly_threshold,
            'baseline_mean': mean,
            'baseline_std': std,
            'deviation': value - mean
        }
    
    def detect_pattern_anomaly(self, data: List[Dict[str, Any]], 
                             pattern_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect pattern-based anomalies in data."""
        anomalies = []
        
        for rule in pattern_rules:
            rule_name = rule['name']
            pattern_func = rule['pattern_function']
            severity = rule.get('severity', AlertSeverity.MEDIUM)
            
            try:
                rule_anomalies = pattern_func(data)
                for anomaly in rule_anomalies:
                    anomalies.append({
                        'rule_name': rule_name,
                        'severity': severity,
                        'anomaly_data': anomaly,
                        'timestamp': datetime.utcnow()
                    })
            except Exception as e:
                logger.error(f"Error in pattern anomaly detection rule '{rule_name}': {e}")
        
        return anomalies
    
    def detect_volume_anomaly(self, current_count: int, 
                            historical_counts: List[int],
                            time_period: str = "hourly") -> Dict[str, Any]:
        """Detect anomalies in data volume."""
        if len(historical_counts) < 5:
            return {'is_anomaly': False, 'reason': 'insufficient_history'}
        
        mean_count = statistics.mean(historical_counts)
        std_count = statistics.stdev(historical_counts)
        
        if std_count == 0:
            is_anomaly = current_count != mean_count
            return {
                'is_anomaly': is_anomaly,
                'reason': 'zero_variance',
                'current_count': current_count,
                'expected_count': mean_count
            }
        
        z_score = abs(current_count - mean_count) / std_count
        is_anomaly = z_score > self.anomaly_threshold
        
        return {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'current_count': current_count,
            'expected_range': (
                mean_count - self.anomaly_threshold * std_count,
                mean_count + self.anomaly_threshold * std_count
            ),
            'time_period': time_period
        }


@dataclass
class DataLineageNode:
    """Represents a node in the data lineage graph."""
    id: str
    name: str
    type: str  # source, transformation, destination
    properties: Dict[str, Any] = field(default_factory=dict)
    upstream_nodes: List[str] = field(default_factory=list)
    downstream_nodes: List[str] = field(default_factory=list)


@dataclass
class DataLineageEdge:
    """Represents an edge in the data lineage graph."""
    source_node: str
    target_node: str
    transformation: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)


class DataLineageTracker:
    """Tracks data lineage and dependencies."""
    
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.quality_impact_map = {}
    
    def add_node(self, node: DataLineageNode):
        """Add a node to the lineage graph."""
        self.nodes[node.id] = node
    
    def add_edge(self, edge: DataLineageEdge):
        """Add an edge to the lineage graph."""
        self.edges.append(edge)
        
        # Update node connections
        if edge.source_node in self.nodes:
            if edge.target_node not in self.nodes[edge.source_node].downstream_nodes:
                self.nodes[edge.source_node].downstream_nodes.append(edge.target_node)
        
        if edge.target_node in self.nodes:
            if edge.source_node not in self.nodes[edge.target_node].upstream_nodes:
                self.nodes[edge.target_node].upstream_nodes.append(edge.source_node)
    
    def trace_lineage_upstream(self, node_id: str) -> List[DataLineageNode]:
        """Trace data lineage upstream from a node."""
        if node_id not in self.nodes:
            return []
        
        visited = set()
        upstream_nodes = []
        
        def _trace_recursive(current_id: str):
            if current_id in visited:
                return
            
            visited.add(current_id)
            current_node = self.nodes[current_id]
            
            for upstream_id in current_node.upstream_nodes:
                if upstream_id in self.nodes:
                    upstream_nodes.append(self.nodes[upstream_id])
                    _trace_recursive(upstream_id)
        
        _trace_recursive(node_id)
        return upstream_nodes
    
    def trace_lineage_downstream(self, node_id: str) -> List[DataLineageNode]:
        """Trace data lineage downstream from a node."""
        if node_id not in self.nodes:
            return []
        
        visited = set()
        downstream_nodes = []
        
        def _trace_recursive(current_id: str):
            if current_id in visited:
                return
            
            visited.add(current_id)
            current_node = self.nodes[current_id]
            
            for downstream_id in current_node.downstream_nodes:
                if downstream_id in self.nodes:
                    downstream_nodes.append(self.nodes[downstream_id])
                    _trace_recursive(downstream_id)
        
        _trace_recursive(node_id)
        return downstream_nodes
    
    def analyze_quality_impact(self, node_id: str, 
                             quality_issues: List[str]) -> Dict[str, Any]:
        """Analyze the impact of quality issues on downstream nodes."""
        if node_id not in self.nodes:
            return {'error': 'Node not found'}
        
        downstream_nodes = self.trace_lineage_downstream(node_id)
        
        impact_analysis = {
            'source_node': node_id,
            'quality_issues': quality_issues,
            'affected_downstream_nodes': len(downstream_nodes),
            'impact_details': []
        }
        
        for downstream_node in downstream_nodes:
            # Calculate impact based on node type and transformation
            impact_severity = self._calculate_impact_severity(
                node_id, downstream_node.id, quality_issues
            )
            
            impact_analysis['impact_details'].append({
                'node_id': downstream_node.id,
                'node_name': downstream_node.name,
                'node_type': downstream_node.type,
                'impact_severity': impact_severity,
                'affected_properties': downstream_node.properties.keys()
            })
        
        return impact_analysis
    
    def _calculate_impact_severity(self, source_id: str, target_id: str, 
                                 quality_issues: List[str]) -> str:
        """Calculate impact severity based on lineage and quality issues."""
        # Find the edge between source and target
        connecting_edge = None
        for edge in self.edges:
            if edge.source_node == source_id and edge.target_node == target_id:
                connecting_edge = edge
                break
        
        # Simplified impact calculation
        high_impact_issues = ['accuracy', 'completeness', 'integrity']
        medium_impact_issues = ['consistency', 'timeliness']
        
        has_high_impact = any(issue in high_impact_issues for issue in quality_issues)
        has_medium_impact = any(issue in medium_impact_issues for issue in quality_issues)
        
        if has_high_impact:
            return 'high'
        elif has_medium_impact:
            return 'medium'
        else:
            return 'low'


class QualityDashboard:
    """Generates data quality dashboard and reports."""
    
    def __init__(self, metrics_service: DataQualityMetrics, 
                 anomaly_detector: AnomalyDetector,
                 lineage_tracker: DataLineageTracker):
        self.metrics_service = metrics_service
        self.anomaly_detector = anomaly_detector
        self.lineage_tracker = lineage_tracker
    
    def generate_summary_report(self, time_window: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """Generate a comprehensive data quality summary report."""
        report = {
            'report_timestamp': datetime.utcnow().isoformat(),
            'time_window_days': time_window.days,
            'metrics_summary': {},
            'alerts_summary': {},
            'trends_summary': {},
            'anomalies_summary': {},
            'overall_score': 0
        }
        
        # Metrics summary
        all_metrics = []
        for metric_name in self.metrics_service.metrics_history.keys():
            recent_metrics = self.metrics_service.get_metric_history(metric_name, time_window)
            if recent_metrics:
                latest_metric = recent_metrics[-1]
                trend = self.metrics_service.get_metric_trend(metric_name, time_window)
                
                report['metrics_summary'][metric_name] = {
                    'current_value': latest_metric.value,
                    'trend': trend['trend'],
                    'change': trend['change'],
                    'is_within_threshold': latest_metric.is_within_threshold,
                    'measurements_count': len(recent_metrics)
                }
                
                all_metrics.append(latest_metric.value)
        
        # Alerts summary
        recent_alerts = [
            alert for alert in self.metrics_service.alerts
            if alert.timestamp >= datetime.utcnow() - time_window
        ]
        
        alert_counts = defaultdict(int)
        for alert in recent_alerts:
            alert_counts[alert.severity.value] += 1
        
        report['alerts_summary'] = {
            'total_alerts': len(recent_alerts),
            'by_severity': dict(alert_counts),
            'unresolved_alerts': len([a for a in recent_alerts if not a.resolved])
        }
        
        # Overall quality score
        if all_metrics:
            report['overall_score'] = statistics.mean(all_metrics)
        
        return report
    
    def generate_metric_dashboard(self, metric_names: List[str]) -> Dict[str, Any]:
        """Generate dashboard data for specific metrics."""
        dashboard = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': {}
        }
        
        for metric_name in metric_names:
            history = self.metrics_service.get_metric_history(
                metric_name, timedelta(days=30)
            )
            
            if history:
                values = [m.value for m in history]
                timestamps = [m.timestamp.isoformat() for m in history]
                
                dashboard['metrics'][metric_name] = {
                    'current_value': values[-1] if values else None,
                    'historical_values': values,
                    'timestamps': timestamps,
                    'statistics': {
                        'mean': statistics.mean(values),
                        'median': statistics.median(values),
                        'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                        'min': min(values),
                        'max': max(values)
                    },
                    'trend': self.metrics_service.get_metric_trend(metric_name)
                }
            else:
                dashboard['metrics'][metric_name] = {
                    'current_value': None,
                    'error': 'No historical data available'
                }
        
        return dashboard
    
    def generate_lineage_report(self, node_id: str) -> Dict[str, Any]:
        """Generate data lineage report for a specific node."""
        if node_id not in self.lineage_tracker.nodes:
            return {'error': f'Node {node_id} not found'}
        
        node = self.lineage_tracker.nodes[node_id]
        upstream_nodes = self.lineage_tracker.trace_lineage_upstream(node_id)
        downstream_nodes = self.lineage_tracker.trace_lineage_downstream(node_id)
        
        return {
            'node_info': {
                'id': node.id,
                'name': node.name,
                'type': node.type,
                'properties': node.properties
            },
            'upstream_dependencies': [
                {'id': n.id, 'name': n.name, 'type': n.type}
                for n in upstream_nodes
            ],
            'downstream_impact': [
                {'id': n.id, 'name': n.name, 'type': n.type}
                for n in downstream_nodes
            ],
            'dependency_count': {
                'upstream': len(upstream_nodes),
                'downstream': len(downstream_nodes)
            }
        }
    
    def export_dashboard_data(self, format_type: str = 'json') -> str:
        """Export dashboard data in specified format."""
        summary = self.generate_summary_report()
        
        if format_type.lower() == 'json':
            return json.dumps(summary, indent=2, default=str)
        elif format_type.lower() == 'csv':
            # Simplified CSV export
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['Metric', 'Current Value', 'Trend', 'Within Threshold'])
            
            # Write data
            for metric_name, data in summary['metrics_summary'].items():
                writer.writerow([
                    metric_name,
                    data['current_value'],
                    data['trend'],
                    data['is_within_threshold']
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format_type}")
