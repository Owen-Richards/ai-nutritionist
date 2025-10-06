"""
Cost Optimization Dashboard and Monitoring
Real-time monitoring and analytics for cost savings
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class CostSavingsMetric:
    timestamp: datetime
    user_phone: str
    optimization_type: str
    cost_saved: float
    request_type: str
    reason: str

class CostOptimizationDashboard:
    """Real-time cost optimization monitoring and analytics"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.cloudwatch = boto3.client('cloudwatch')
        
        # Tables for cost optimization tracking
        self.optimization_metrics_table = self.dynamodb.Table('ai-nutritionist-optimization-metrics')
        self.cost_trends_table = self.dynamodb.Table('ai-nutritionist-cost-trends')
        self.user_efficiency_table = self.dynamodb.Table('ai-nutritionist-user-efficiency')

    def get_realtime_savings_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Generate real-time cost savings dashboard"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get optimization metrics for the time period
            metrics = self._get_optimization_metrics(start_time, end_time)
            
            # Calculate key metrics
            total_requests = len(metrics)
            optimized_requests = len([m for m in metrics if m.cost_saved > 0])
            total_cost_saved = sum(m.cost_saved for m in metrics)
            
            # Optimization breakdown
            optimization_breakdown = self._calculate_optimization_breakdown(metrics)
            
            # Top cost-saving optimizations
            top_optimizations = self._get_top_optimizations(metrics)
            
            # Cost efficiency trends
            efficiency_trends = self._calculate_efficiency_trends(metrics, hours)
            
            # User behavior insights
            user_insights = self._analyze_user_behavior(metrics)
            
            return {
                'summary': {
                    'time_period_hours': hours,
                    'total_requests': total_requests,
                    'optimized_requests': optimized_requests,
                    'optimization_rate': round((optimized_requests / max(total_requests, 1)) * 100, 2),
                    'total_cost_saved': round(total_cost_saved, 4),
                    'average_cost_saved_per_optimization': round(total_cost_saved / max(optimized_requests, 1), 4),
                    'estimated_monthly_savings': round(total_cost_saved * (30 * 24 / hours), 2)
                },
                'optimization_breakdown': optimization_breakdown,
                'top_optimizations': top_optimizations,
                'efficiency_trends': efficiency_trends,
                'user_insights': user_insights,
                'recommendations': self._generate_optimization_recommendations(metrics)
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {str(e)}")
            return {'error': 'Unable to generate dashboard at this time'}

    def get_user_cost_analysis(self, user_phone: str, days: int = 30) -> Dict[str, Any]:
        """Detailed cost analysis for a specific user"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Get user's optimization history
            user_metrics = self._get_user_optimization_metrics(user_phone, start_time, end_time)
            
            # Calculate user-specific insights
            total_requests = len(user_metrics)
            total_saved = sum(m.cost_saved for m in user_metrics)
            optimization_types = {}
            
            for metric in user_metrics:
                opt_type = metric.optimization_type
                if opt_type not in optimization_types:
                    optimization_types[opt_type] = {'count': 0, 'savings': 0.0}
                optimization_types[opt_type]['count'] += 1
                optimization_types[opt_type]['savings'] += metric.cost_saved
            
            # User behavior patterns
            request_patterns = self._analyze_user_request_patterns(user_metrics)
            
            # Cost efficiency score
            efficiency_score = self._calculate_user_efficiency_score(user_phone, user_metrics)
            
            # Personalized recommendations
            recommendations = self._generate_user_recommendations(user_phone, user_metrics)
            
            return {
                'user_phone': user_phone,
                'analysis_period_days': days,
                'summary': {
                    'total_requests': total_requests,
                    'total_cost_saved': round(total_saved, 4),
                    'efficiency_score': efficiency_score,
                    'optimization_rate': round(len([m for m in user_metrics if m.cost_saved > 0]) / max(total_requests, 1) * 100, 2)
                },
                'optimization_breakdown': optimization_types,
                'request_patterns': request_patterns,
                'recommendations': recommendations,
                'cost_trends': self._get_user_cost_trends(user_phone, start_time, end_time)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user costs: {str(e)}")
            return {'error': 'Unable to analyze user costs at this time'}

    def generate_cost_optimization_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts for cost optimization opportunities"""
        alerts = []
        
        try:
            # Alert 1: Users approaching cost limits
            high_cost_users = self._identify_high_cost_users()
            for user_data in high_cost_users:
                alerts.append({
                    'type': 'high_cost_user',
                    'priority': 'high',
                    'user_phone': user_data['phone'],
                    'daily_cost': user_data['cost'],
                    'message': f"User {user_data['phone']} approaching daily cost limit (${user_data['cost']:.2f})",
                    'recommended_action': 'Consider upgrading to premium or implementing additional throttling'
                })
            
            # Alert 2: Spike in rejected requests
            rejection_spike = self._detect_rejection_spike()
            if rejection_spike:
                alerts.append({
                    'type': 'rejection_spike',
                    'priority': 'medium',
                    'rejection_rate': rejection_spike['rate'],
                    'message': f"Rejection rate spike detected: {rejection_spike['rate']:.1f}%",
                    'recommended_action': 'Review spam protection settings or user education'
                })
            
            # Alert 3: Low-value request increase
            low_value_increase = self._detect_low_value_requests()
            if low_value_increase:
                alerts.append({
                    'type': 'low_value_increase',
                    'priority': 'low',
                    'increase_rate': low_value_increase['rate'],
                    'message': f"Increase in low-value requests: {low_value_increase['rate']:.1f}%",
                    'recommended_action': 'Consider user education or request type optimization'
                })
            
            # Alert 4: Cost optimization opportunities
            optimization_opportunities = self._identify_optimization_opportunities()
            for opportunity in optimization_opportunities:
                alerts.append({
                    'type': 'optimization_opportunity',
                    'priority': 'medium',
                    'opportunity_type': opportunity['type'],
                    'potential_savings': opportunity['savings'],
                    'message': f"Optimization opportunity: {opportunity['description']}",
                    'recommended_action': opportunity['action']
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating alerts: {str(e)}")
            return [{'type': 'error', 'message': 'Unable to generate alerts'}]

    def track_cost_optimization_success(self, optimization_type: str, cost_saved: float, user_phone: str, request_type: str, reason: str):
        """Track successful cost optimization for analytics"""
        try:
            metric = CostSavingsMetric(
                timestamp=datetime.utcnow(),
                user_phone=user_phone,
                optimization_type=optimization_type,
                cost_saved=cost_saved,
                request_type=request_type,
                reason=reason
            )
            
            # Store in DynamoDB
            self.optimization_metrics_table.put_item(
                Item={
                    'timestamp': int(metric.timestamp.timestamp()),
                    'user_phone': metric.user_phone,
                    'optimization_type': metric.optimization_type,
                    'cost_saved': Decimal(str(metric.cost_saved)),
                    'request_type': metric.request_type,
                    'reason': metric.reason,
                    'date': metric.timestamp.strftime('%Y-%m-%d'),
                    'hour': metric.timestamp.strftime('%Y-%m-%d-%H'),
                    'ttl': int(metric.timestamp.timestamp()) + (90 * 24 * 60 * 60)  # 90 days
                }
            )
            
            # Send CloudWatch metrics
            self.cloudwatch.put_metric_data(
                Namespace='AI-Nutritionist/CostOptimization',
                MetricData=[
                    {
                        'MetricName': 'CostSaved',
                        'Value': cost_saved,
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'OptimizationType', 'Value': optimization_type},
                            {'Name': 'RequestType', 'Value': request_type}
                        ]
                    },
                    {
                        'MetricName': 'OptimizationCount',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'OptimizationType', 'Value': optimization_type}
                        ]
                    }
                ]
            )
            
        except Exception as e:
            logger.error(f"Error tracking optimization success: {str(e)}")

    def _get_optimization_metrics(self, start_time: datetime, end_time: datetime) -> List[CostSavingsMetric]:
        """Get optimization metrics for a time period"""
        # Implementation would query DynamoDB for metrics in the time range
        # For now, return empty list
        return []

    def _get_user_optimization_metrics(self, user_phone: str, start_time: datetime, end_time: datetime) -> List[CostSavingsMetric]:
        """Get optimization metrics for a specific user"""
        # Implementation would query DynamoDB for user-specific metrics
        return []

    def _calculate_optimization_breakdown(self, metrics: List[CostSavingsMetric]) -> Dict[str, Any]:
        """Calculate breakdown of optimization types"""
        breakdown = {}
        for metric in metrics:
            opt_type = metric.optimization_type
            if opt_type not in breakdown:
                breakdown[opt_type] = {'count': 0, 'total_saved': 0.0}
            breakdown[opt_type]['count'] += 1
            breakdown[opt_type]['total_saved'] += metric.cost_saved
        
        return breakdown

    def _get_top_optimizations(self, metrics: List[CostSavingsMetric], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top cost-saving optimizations"""
        optimization_savings = {}
        for metric in metrics:
            key = f"{metric.optimization_type}_{metric.reason}"
            if key not in optimization_savings:
                optimization_savings[key] = {
                    'type': metric.optimization_type,
                    'reason': metric.reason,
                    'count': 0,
                    'total_saved': 0.0
                }
            optimization_savings[key]['count'] += 1
            optimization_savings[key]['total_saved'] += metric.cost_saved
        
        # Sort by total savings
        sorted_optimizations = sorted(
            optimization_savings.values(),
            key=lambda x: x['total_saved'],
            reverse=True
        )
        
        return sorted_optimizations[:limit]

    def _calculate_efficiency_trends(self, metrics: List[CostSavingsMetric], hours: int) -> Dict[str, Any]:
        """Calculate efficiency trends over time"""
        hourly_data = {}
        for metric in metrics:
            hour_key = metric.timestamp.strftime('%Y-%m-%d-%H')
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {'requests': 0, 'optimized': 0, 'savings': 0.0}
            hourly_data[hour_key]['requests'] += 1
            if metric.cost_saved > 0:
                hourly_data[hour_key]['optimized'] += 1
                hourly_data[hour_key]['savings'] += metric.cost_saved
        
        return {
            'hourly_breakdown': hourly_data,
            'trend_direction': 'improving',  # Calculate actual trend
            'average_hourly_savings': sum(h['savings'] for h in hourly_data.values()) / max(len(hourly_data), 1)
        }

    def _analyze_user_behavior(self, metrics: List[CostSavingsMetric]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        user_data = {}
        for metric in metrics:
            if metric.user_phone not in user_data:
                user_data[metric.user_phone] = {'requests': 0, 'optimized': 0, 'savings': 0.0}
            user_data[metric.user_phone]['requests'] += 1
            if metric.cost_saved > 0:
                user_data[metric.user_phone]['optimized'] += 1
                user_data[metric.user_phone]['savings'] += metric.cost_saved
        
        return {
            'total_unique_users': len(user_data),
            'high_optimization_users': len([u for u in user_data.values() if u['optimized'] / max(u['requests'], 1) > 0.5]),
            'average_savings_per_user': sum(u['savings'] for u in user_data.values()) / max(len(user_data), 1)
        }

    def _generate_optimization_recommendations(self, metrics: List[CostSavingsMetric]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on metrics"""
        recommendations = []
        
        # Analyze patterns and generate recommendations
        spam_count = len([m for m in metrics if 'spam' in m.reason.lower()])
        duplicate_count = len([m for m in metrics if 'duplicate' in m.reason.lower()])
        
        if spam_count > len(metrics) * 0.3:  # More than 30% spam
            recommendations.append({
                'type': 'spam_protection',
                'priority': 'high',
                'description': 'High spam detection rate suggests need for enhanced filtering',
                'action': 'Review and update spam detection algorithms',
                'potential_impact': 'High cost savings'
            })
        
        if duplicate_count > len(metrics) * 0.2:  # More than 20% duplicates
            recommendations.append({
                'type': 'duplicate_prevention',
                'priority': 'medium',
                'description': 'Many duplicate requests detected',
                'action': 'Implement smarter duplicate detection or user education',
                'potential_impact': 'Medium cost savings'
            })
        
        return recommendations

    # Additional helper methods would be implemented here...
    def _identify_high_cost_users(self) -> List[Dict[str, Any]]:
        """Identify users with high costs"""
        return []  # Implementation would query cost data
    
    def _detect_rejection_spike(self) -> Optional[Dict[str, Any]]:
        """Detect spikes in request rejections"""
        return None  # Implementation would analyze trends
    
    def _detect_low_value_requests(self) -> Optional[Dict[str, Any]]:
        """Detect increases in low-value requests"""
        return None  # Implementation would analyze request patterns
    
    def _identify_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Identify new optimization opportunities"""
        return []  # Implementation would analyze patterns
    
    def _analyze_user_request_patterns(self, metrics: List[CostSavingsMetric]) -> Dict[str, Any]:
        """Analyze user's request patterns"""
        return {}  # Implementation would analyze patterns
    
    def _calculate_user_efficiency_score(self, user_phone: str, metrics: List[CostSavingsMetric]) -> float:
        """Calculate user's efficiency score"""
        return 0.85  # Implementation would calculate actual score
    
    def _generate_user_recommendations(self, user_phone: str, metrics: List[CostSavingsMetric]) -> List[Dict[str, Any]]:
        """Generate user-specific recommendations"""
        return []  # Implementation would generate recommendations
    
    def _get_user_cost_trends(self, user_phone: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get cost trends for a user"""
        return {}  # Implementation would query trend data

# Integration function for real-time monitoring
def lambda_cost_optimization_monitor(event, context):
    """Lambda function for cost optimization monitoring"""
    try:
        dashboard = CostOptimizationDashboard()
        
        action = event.get('action', 'dashboard')
        
        if action == 'dashboard':
            hours = event.get('hours', 24)
            return {
                'statusCode': 200,
                'body': json.dumps(dashboard.get_realtime_savings_dashboard(hours))
            }
        
        elif action == 'user_analysis':
            user_phone = event.get('user_phone')
            days = event.get('days', 30)
            return {
                'statusCode': 200,
                'body': json.dumps(dashboard.get_user_cost_analysis(user_phone, days))
            }
        
        elif action == 'alerts':
            return {
                'statusCode': 200,
                'body': json.dumps(dashboard.generate_cost_optimization_alerts())
            }
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'})
            }
    
    except Exception as e:
        logger.error(f"Error in cost optimization monitor: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
