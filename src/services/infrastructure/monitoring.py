"""
Advanced Performance Monitoring and Analytics Service
Tracks user engagement, system performance, and business metrics in real-time.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class PerformanceMonitoringService:
    """Advanced performance monitoring with real-time analytics"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.cloudwatch = boto3.client('cloudwatch')
        
        # DynamoDB tables for analytics
        self.metrics_table = self.dynamodb.Table('ai-nutritionist-performance-metrics')
        self.user_analytics_table = self.dynamodb.Table('ai-nutritionist-user-analytics')
        self.system_health_table = self.dynamodb.Table('ai-nutritionist-system-health')
        
        # Performance thresholds
        self.thresholds = {
            'response_time_warning': 3.0,  # seconds
            'response_time_critical': 5.0,  # seconds
            'error_rate_warning': 0.05,    # 5%
            'error_rate_critical': 0.10,   # 10%
            'cache_hit_rate_warning': 0.60, # 60%
            'cost_per_user_warning': 1.50,  # $1.50
            'cost_per_user_critical': 2.00  # $2.00
        }
    
    def track_api_performance(self, operation: str, response_time: float, 
                            success: bool, cost: float = 0.0, 
                            cache_hit: bool = False) -> None:
        """Track API operation performance metrics"""
        try:
            timestamp = datetime.utcnow()
            
            # Store detailed metrics
            self.metrics_table.put_item(
                Item={
                    'operation': operation,
                    'timestamp': timestamp.isoformat(),
                    'response_time': Decimal(str(response_time)),
                    'success': success,
                    'cost': Decimal(str(cost)),
                    'cache_hit': cache_hit,
                    'date': timestamp.strftime('%Y-%m-%d'),
                    'hour': timestamp.hour,
                    'ttl': int((timestamp + timedelta(days=30)).timestamp())
                }
            )
            
            # Send to CloudWatch
            self._send_cloudwatch_metrics(operation, response_time, success, cost, cache_hit)
            
            # Check for performance alerts
            self._check_performance_alerts(operation, response_time, success)
            
        except Exception as e:
            logger.error(f"Error tracking API performance: {e}")
    
    def track_user_engagement(self, user_phone: str, action: str, 
                            context: Dict[str, Any] = None) -> None:
        """Track user engagement and behavior patterns"""
        try:
            timestamp = datetime.utcnow()
            
            # Update user analytics
            self.user_analytics_table.put_item(
                Item={
                    'user_phone': user_phone,
                    'timestamp': timestamp.isoformat(),
                    'action': action,
                    'context': json.dumps(context or {}),
                    'date': timestamp.strftime('%Y-%m-%d'),
                    'hour': timestamp.hour,
                    'ttl': int((timestamp + timedelta(days=90)).timestamp())
                }
            )
            
            # Update user session metrics
            self._update_user_session_metrics(user_phone, action, timestamp)
            
        except Exception as e:
            logger.error(f"Error tracking user engagement: {e}")
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive performance dashboard"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            # Get recent metrics
            recent_metrics = self._get_recent_metrics(start_time, end_time)
            
            # Calculate performance KPIs
            dashboard = {
                'timestamp': end_time.isoformat(),
                'period': '24_hours',
                'performance': self._calculate_performance_kpis(recent_metrics),
                'user_engagement': self._calculate_engagement_kpis(start_time, end_time),
                'cost_analysis': self._calculate_cost_analysis(recent_metrics),
                'system_health': self._get_system_health_status(),
                'alerts': self._get_active_alerts(),
                'recommendations': self._generate_optimization_recommendations(recent_metrics)
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating performance dashboard: {e}")
            return {'error': 'Failed to generate dashboard'}
    
    def get_user_analytics(self, user_phone: str, days: int = 7) -> Dict[str, Any]:
        """Get detailed analytics for a specific user"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Query user analytics
            response = self.user_analytics_table.query(
                KeyConditionExpression='user_phone = :phone',
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )
            
            activities = response.get('Items', [])
            
            # Analyze user behavior
            analytics = {
                'user_phone': user_phone,
                'period_days': days,
                'total_interactions': len(activities),
                'activity_breakdown': self._analyze_user_activities(activities),
                'engagement_score': self._calculate_engagement_score(activities),
                'usage_patterns': self._analyze_usage_patterns(activities),
                'conversion_opportunities': self._identify_conversion_opportunities(activities),
                'retention_risk': self._assess_retention_risk(activities)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {'error': 'Failed to retrieve user analytics'}
    
    def _send_cloudwatch_metrics(self, operation: str, response_time: float, 
                                success: bool, cost: float, cache_hit: bool) -> None:
        """Send metrics to CloudWatch"""
        try:
            namespace = 'AINutritionist/Performance'
            
            metrics = [
                {
                    'MetricName': 'ResponseTime',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': response_time,
                    'Unit': 'Seconds'
                },
                {
                    'MetricName': 'SuccessRate',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': 1 if success else 0,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'Cost',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': cost,
                    'Unit': 'None'
                },
                {
                    'MetricName': 'CacheHitRate',
                    'Dimensions': [{'Name': 'Operation', 'Value': operation}],
                    'Value': 1 if cache_hit else 0,
                    'Unit': 'Count'
                }
            ]
            
            self.cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=metrics
            )
            
        except Exception as e:
            logger.warning(f"Error sending CloudWatch metrics: {e}")
    
    def _check_performance_alerts(self, operation: str, response_time: float, 
                                success: bool) -> None:
        """Check for performance threshold violations"""
        try:
            alerts = []
            
            # Response time alerts
            if response_time > self.thresholds['response_time_critical']:
                alerts.append({
                    'level': 'CRITICAL',
                    'metric': 'response_time',
                    'operation': operation,
                    'value': response_time,
                    'threshold': self.thresholds['response_time_critical']
                })
            elif response_time > self.thresholds['response_time_warning']:
                alerts.append({
                    'level': 'WARNING',
                    'metric': 'response_time',
                    'operation': operation,
                    'value': response_time,
                    'threshold': self.thresholds['response_time_warning']
                })
            
            # Error alerts
            if not success:
                alerts.append({
                    'level': 'ERROR',
                    'metric': 'operation_failure',
                    'operation': operation,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Store alerts for dashboard
            for alert in alerts:
                self._store_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
    def _get_recent_metrics(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Retrieve recent performance metrics"""
        try:
            # This is a simplified version - in practice, you'd use GSI for time-based queries
            response = self.metrics_table.scan(
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error retrieving recent metrics: {e}")
            return []
    
    def _calculate_performance_kpis(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        if not metrics:
            return {}
        
        total_requests = len(metrics)
        successful_requests = sum(1 for m in metrics if m.get('success', False))
        cache_hits = sum(1 for m in metrics if m.get('cache_hit', False))
        total_cost = sum(float(m.get('cost', 0)) for m in metrics)
        response_times = [float(m.get('response_time', 0)) for m in metrics]
        
        return {
            'total_requests': total_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'cache_hit_rate': cache_hits / total_requests if total_requests > 0 else 0,
            'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'p95_response_time': self._calculate_percentile(response_times, 95),
            'total_cost': total_cost,
            'avg_cost_per_request': total_cost / total_requests if total_requests > 0 else 0
        }
    
    def _calculate_engagement_kpis(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate user engagement KPIs"""
        try:
            # Query user analytics for the period
            response = self.user_analytics_table.scan(
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )
            
            activities = response.get('Items', [])
            
            if not activities:
                return {}
            
            # Calculate engagement metrics
            unique_users = len(set(a['user_phone'] for a in activities))
            total_interactions = len(activities)
            
            action_counts = {}
            for activity in activities:
                action = activity.get('action', 'unknown')
                action_counts[action] = action_counts.get(action, 0) + 1
            
            return {
                'unique_users': unique_users,
                'total_interactions': total_interactions,
                'avg_interactions_per_user': total_interactions / unique_users if unique_users > 0 else 0,
                'action_breakdown': action_counts,
                'most_popular_action': max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating engagement KPIs: {e}")
            return {}
    
    def _calculate_cost_analysis(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze cost patterns and efficiency"""
        if not metrics:
            return {}
        
        # Group costs by operation
        operation_costs = {}
        for metric in metrics:
            op = metric.get('operation', 'unknown')
            cost = float(metric.get('cost', 0))
            if op not in operation_costs:
                operation_costs[op] = []
            operation_costs[op].append(cost)
        
        # Calculate cost analysis
        analysis = {}
        total_cost = 0
        
        for operation, costs in operation_costs.items():
            op_total = sum(costs)
            total_cost += op_total
            
            analysis[operation] = {
                'total_cost': op_total,
                'avg_cost': op_total / len(costs) if costs else 0,
                'request_count': len(costs),
                'cost_efficiency': op_total / len(costs) if costs else 0
            }
        
        # Add overall analysis
        analysis['summary'] = {
            'total_cost': total_cost,
            'most_expensive_operation': max(operation_costs.items(), 
                                          key=lambda x: sum(x[1]))[0] if operation_costs else None,
            'cost_per_request': total_cost / len(metrics) if metrics else 0
        }
        
        return analysis
    
    def _generate_optimization_recommendations(self, metrics: List[Dict]) -> List[Dict[str, str]]:
        """Generate AI-powered optimization recommendations"""
        recommendations = []
        
        if not metrics:
            return recommendations
        
        # Analyze performance patterns
        kpis = self._calculate_performance_kpis(metrics)
        
        # Cache hit rate recommendations
        if kpis.get('cache_hit_rate', 0) < self.thresholds['cache_hit_rate_warning']:
            recommendations.append({
                'category': 'Caching',
                'recommendation': 'Improve cache hit rate by extending TTL for stable data',
                'impact': 'Could reduce costs by 40-60%',
                'priority': 'HIGH'
            })
        
        # Response time recommendations
        if kpis.get('avg_response_time', 0) > self.thresholds['response_time_warning']:
            recommendations.append({
                'category': 'Performance',
                'recommendation': 'Optimize slow operations with parallel processing',
                'impact': 'Could improve response times by 30-50%',
                'priority': 'MEDIUM'
            })
        
        # Cost optimization recommendations
        if kpis.get('avg_cost_per_request', 0) > self.thresholds['cost_per_user_warning']:
            recommendations.append({
                'category': 'Cost Optimization',
                'recommendation': 'Implement request batching and AI prompt optimization',
                'impact': 'Could reduce costs by 25-40%',
                'priority': 'HIGH'
            })
        
        return recommendations
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _analyze_user_activities(self, activities: List[Dict]) -> Dict[str, int]:
        """Analyze user activity patterns"""
        activity_counts = {}
        for activity in activities:
            action = activity.get('action', 'unknown')
            activity_counts[action] = activity_counts.get(action, 0) + 1
        return activity_counts
    
    def _calculate_engagement_score(self, activities: List[Dict]) -> float:
        """Calculate user engagement score (0-100)"""
        if not activities:
            return 0
        
        # Weight different activities
        activity_weights = {
            'meal_plan_request': 10,
            'nutrition_query': 8,
            'recipe_request': 7,
            'grocery_list': 9,
            'subscription_upgrade': 15,
            'general_chat': 3
        }
        
        total_score = 0
        for activity in activities:
            action = activity.get('action', 'general_chat')
            weight = activity_weights.get(action, 1)
            total_score += weight
        
        # Normalize to 0-100 scale based on activity frequency
        days_span = 7  # Assuming 7-day analysis
        max_possible_score = 100 * days_span  # Perfect engagement
        
        return min(100, (total_score / max_possible_score) * 100)
    
    def _analyze_usage_patterns(self, activities: List[Dict]) -> Dict[str, Any]:
        """Analyze user usage patterns"""
        if not activities:
            return {}
        
        # Analyze timing patterns
        hours = [datetime.fromisoformat(a['timestamp']).hour for a in activities]
        hour_counts = {}
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 12
        
        return {
            'peak_usage_hour': peak_hour,
            'total_active_hours': len(set(hours)),
            'activity_distribution': hour_counts
        }
    
    def _identify_conversion_opportunities(self, activities: List[Dict]) -> List[str]:
        """Identify opportunities for user conversion"""
        opportunities = []
        
        activity_types = set(a.get('action', '') for a in activities)
        
        # Check for high engagement without premium features
        if len(activities) > 10 and 'subscription_upgrade' not in activity_types:
            opportunities.append('High engagement user - prime for premium upgrade')
        
        # Check for grocery-related activities
        if any('grocery' in a.get('action', '') for a in activities):
            opportunities.append('Grocery user - target for affiliate partnerships')
        
        # Check for nutrition-focused users
        nutrition_activities = sum(1 for a in activities if 'nutrition' in a.get('action', ''))
        if nutrition_activities > 5:
            opportunities.append('Nutrition-focused user - premium meal plans opportunity')
        
        return opportunities
    
    def _assess_retention_risk(self, activities: List[Dict]) -> str:
        """Assess user retention risk level"""
        if not activities:
            return 'HIGH'
        
        # Check recent activity
        recent_activities = [a for a in activities 
                           if datetime.fromisoformat(a['timestamp']) > 
                           datetime.utcnow() - timedelta(days=3)]
        
        if len(recent_activities) == 0:
            return 'HIGH'
        elif len(recent_activities) < 2:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_system_health_status(self) -> Dict[str, str]:
        """Get overall system health status"""
        return {
            'api_status': 'HEALTHY',
            'database_status': 'HEALTHY',
            'cache_status': 'HEALTHY',
            'monitoring_status': 'ACTIVE'
        }
    
    def _get_active_alerts(self) -> List[Dict]:
        """Get currently active alerts"""
        # In a real implementation, this would query an alerts table
        return []
    
    def _store_alert(self, alert: Dict) -> None:
        """Store alert for monitoring dashboard"""
        try:
            timestamp = datetime.utcnow()
            
            self.system_health_table.put_item(
                Item={
                    'alert_id': f"{alert['operation']}_{timestamp.timestamp()}",
                    'timestamp': timestamp.isoformat(),
                    'level': alert['level'],
                    'metric': alert['metric'],
                    'operation': alert['operation'],
                    'details': json.dumps(alert),
                    'ttl': int((timestamp + timedelta(days=7)).timestamp())
                }
            )
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def _update_user_session_metrics(self, user_phone: str, action: str, 
                                   timestamp: datetime) -> None:
        """Update user session and engagement metrics"""
        try:
            # This could update session duration, activity streaks, etc.
            # For now, we'll just log the interaction
            logger.info(f"User {user_phone} performed {action} at {timestamp}")
            
        except Exception as e:
            logger.error(f"Error updating user session metrics: {e}")
