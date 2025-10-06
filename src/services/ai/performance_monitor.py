"""
AI Performance Monitoring Dashboard
Real-time monitoring, analytics, and optimization recommendations
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import boto3
from dataclasses import dataclass, asdict
import logging

from .enhanced_service import enhanced_ai_service
from .prompt_engine import prompt_engine
from ...config.ai_config import ai_config

logger = logging.getLogger(__name__)


@dataclass
class AIPerformanceSnapshot:
    """Snapshot of AI performance metrics"""
    timestamp: str
    total_requests: int
    cache_hit_rate: float
    error_rate: float
    avg_response_time: float
    cost_per_request: float
    top_model: str
    optimization_score: float


class AIPerformanceMonitor:
    """
    Advanced AI performance monitoring with real-time analytics
    """
    
    def __init__(self):
        # Initialize AWS clients with error handling for testing
        try:
            self.cloudwatch = boto3.client('cloudwatch')
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}")
            self.cloudwatch = None
        
        self.performance_history: List[AIPerformanceSnapshot] = []
        self.alerts_config = {
            'error_rate_threshold': 0.1,  # 10%
            'response_time_threshold': 3.0,  # 3 seconds
            'cost_threshold': 0.05,  # $0.05 per request
            'cache_hit_rate_min': 0.5  # 50%
        }
        
    async def collect_real_time_metrics(self) -> Dict[str, Any]:
        """
        Collect comprehensive real-time AI performance metrics
        """
        # Get AI service metrics
        ai_metrics = enhanced_ai_service.get_performance_metrics()
        
        # Get prompt analytics
        prompt_analytics = prompt_engine.get_prompt_analytics()
        
        # Get caching metrics
        cache_metrics = enhanced_ai_service.caching_service.get_cache_analytics()
        
        # Calculate performance scores
        performance_scores = self._calculate_performance_scores(ai_metrics)
        
        # Generate optimization recommendations
        recommendations = self._generate_ai_optimization_recommendations(
            ai_metrics, prompt_analytics, cache_metrics
        )
        
        # Create performance snapshot
        snapshot = AIPerformanceSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            total_requests=ai_metrics.get('total_requests', 0),
            cache_hit_rate=ai_metrics.get('cache_hit_rate', 0.0),
            error_rate=ai_metrics.get('error_rate', 0.0),
            avg_response_time=ai_metrics.get('avg_response_time', 0.0),
            cost_per_request=ai_metrics.get('cost_per_request', 0.0),
            top_model=self._get_top_model(ai_metrics),
            optimization_score=performance_scores['overall_score']
        )
        
        # Store snapshot
        self.performance_history.append(snapshot)
        
        # Keep only last 100 snapshots
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
        
        return {
            'current_metrics': ai_metrics,
            'prompt_analytics': prompt_analytics,
            'cache_analytics': cache_metrics,
            'performance_scores': performance_scores,
            'recommendations': recommendations,
            'alerts': self._check_performance_alerts(ai_metrics),
            'trends': self._calculate_performance_trends(),
            'cost_analysis': self._analyze_cost_efficiency(ai_metrics),
            'model_performance': self._analyze_model_performance(ai_metrics)
        }
    
    def _calculate_performance_scores(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate performance scores (0-100 scale)
        """
        if metrics.get('total_requests', 0) == 0:
            return {
                'reliability_score': 100.0,
                'efficiency_score': 100.0,
                'cost_score': 100.0,
                'speed_score': 100.0,
                'overall_score': 100.0
            }
        
        # Reliability score (based on error rate)
        error_rate = metrics.get('error_rate', 0.0)
        reliability_score = max(0, 100 - (error_rate * 1000))  # 10% error = 0 score
        
        # Efficiency score (based on cache hit rate)
        cache_hit_rate = metrics.get('cache_hit_rate', 0.0)
        efficiency_score = cache_hit_rate * 100
        
        # Cost score (based on cost per request)
        cost_per_request = metrics.get('cost_per_request', 0.0)
        cost_score = max(0, 100 - (cost_per_request * 2000))  # $0.05 = 0 score
        
        # Speed score (based on response time)
        avg_response_time = metrics.get('avg_response_time', 0.0)
        speed_score = max(0, 100 - (avg_response_time * 25))  # 4 seconds = 0 score
        
        # Overall score (weighted average)
        overall_score = (
            reliability_score * 0.3 +
            efficiency_score * 0.25 +
            cost_score * 0.25 +
            speed_score * 0.2
        )
        
        return {
            'reliability_score': round(reliability_score, 1),
            'efficiency_score': round(efficiency_score, 1),
            'cost_score': round(cost_score, 1),
            'speed_score': round(speed_score, 1),
            'overall_score': round(overall_score, 1)
        }
    
    def _generate_ai_optimization_recommendations(self, ai_metrics: Dict[str, Any],
                                                prompt_analytics: Dict[str, Any],
                                                cache_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate AI-specific optimization recommendations
        """
        recommendations = []
        
        # AI Service Optimizations
        if ai_metrics.get('error_rate', 0) > 0.05:
            recommendations.append({
                'category': 'Reliability',
                'priority': 'HIGH',
                'title': 'High AI Error Rate Detected',
                'description': f"Error rate is {ai_metrics['error_rate']:.2%}, consider implementing better fallbacks",
                'action': 'Review model fallback chain and add more resilient error handling',
                'estimated_impact': 'Reduce errors by 60-80%'
            })
        
        if ai_metrics.get('avg_response_time', 0) > 2.0:
            recommendations.append({
                'category': 'Performance',
                'priority': 'MEDIUM',
                'title': 'Slow AI Response Times',
                'description': f"Average response time is {ai_metrics['avg_response_time']:.2f}s",
                'action': 'Consider using faster models for simple queries or implement parallel processing',
                'estimated_impact': 'Improve response times by 30-50%'
            })
        
        if ai_metrics.get('cost_per_request', 0) > 0.02:
            recommendations.append({
                'category': 'Cost Optimization',
                'priority': 'HIGH',
                'title': 'High AI Costs',
                'description': f"Cost per request is ${ai_metrics['cost_per_request']:.4f}",
                'action': 'Optimize prompts, use cheaper models for simple tasks, or extend cache TTL',
                'estimated_impact': 'Reduce costs by 40-70%'
            })
        
        # Prompt Optimizations
        if 'optimization_opportunities' in prompt_analytics:
            for opportunity in prompt_analytics['optimization_opportunities']:
                recommendations.append({
                    'category': 'Prompt Optimization',
                    'priority': 'MEDIUM',
                    'title': 'Prompt Efficiency Opportunity',
                    'description': opportunity,
                    'action': 'Optimize prompt templates to reduce token usage',
                    'estimated_impact': 'Reduce costs by 10-20%'
                })
        
        # Cache Optimizations
        cache_hit_rate = cache_metrics.get('performance', {}).get('hit_rate', 0)
        if cache_hit_rate < 0.6:
            recommendations.append({
                'category': 'Caching',
                'priority': 'HIGH',
                'title': 'Low Cache Hit Rate',
                'description': f"Cache hit rate is {cache_hit_rate:.2%}",
                'action': 'Extend cache TTL for stable data or improve cache key strategy',
                'estimated_impact': 'Improve performance by 40-60% and reduce costs by 30-50%'
            })
        
        # Model Usage Optimizations
        model_usage = ai_metrics.get('model_usage_distribution', {})
        if model_usage:
            expensive_models = ['claude-3-opus', 'claude-3-sonnet']
            total_requests = sum(model_usage.values())
            expensive_usage = sum(count for model, count in model_usage.items() 
                                if any(exp in model for exp in expensive_models))
            
            if expensive_usage / max(total_requests, 1) > 0.3:
                recommendations.append({
                    'category': 'Model Selection',
                    'priority': 'MEDIUM',
                    'title': 'Optimize Model Selection',
                    'description': f"Using expensive models for {expensive_usage/total_requests:.1%} of requests",
                    'action': 'Review use cases and switch to cheaper models where appropriate',
                    'estimated_impact': 'Reduce costs by 20-40%'
                })
        
        return recommendations
    
    def _check_performance_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for performance alerts based on thresholds
        """
        alerts = []
        
        # Error rate alert
        error_rate = metrics.get('error_rate', 0.0)
        if error_rate > self.alerts_config['error_rate_threshold']:
            alerts.append({
                'severity': 'CRITICAL',
                'type': 'ERROR_RATE',
                'message': f"High error rate: {error_rate:.2%}",
                'threshold': self.alerts_config['error_rate_threshold'],
                'current': error_rate
            })
        
        # Response time alert
        response_time = metrics.get('avg_response_time', 0.0)
        if response_time > self.alerts_config['response_time_threshold']:
            alerts.append({
                'severity': 'WARNING',
                'type': 'RESPONSE_TIME',
                'message': f"Slow response time: {response_time:.2f}s",
                'threshold': self.alerts_config['response_time_threshold'],
                'current': response_time
            })
        
        # Cost alert
        cost_per_request = metrics.get('cost_per_request', 0.0)
        if cost_per_request > self.alerts_config['cost_threshold']:
            alerts.append({
                'severity': 'WARNING',
                'type': 'HIGH_COST',
                'message': f"High cost per request: ${cost_per_request:.4f}",
                'threshold': self.alerts_config['cost_threshold'],
                'current': cost_per_request
            })
        
        # Cache hit rate alert
        cache_hit_rate = metrics.get('cache_hit_rate', 0.0)
        if cache_hit_rate < self.alerts_config['cache_hit_rate_min']:
            alerts.append({
                'severity': 'INFO',
                'type': 'LOW_CACHE_HIT_RATE',
                'message': f"Low cache hit rate: {cache_hit_rate:.2%}",
                'threshold': self.alerts_config['cache_hit_rate_min'],
                'current': cache_hit_rate
            })
        
        return alerts
    
    def _calculate_performance_trends(self) -> Dict[str, Any]:
        """
        Calculate performance trends from historical data
        """
        if len(self.performance_history) < 2:
            return {'message': 'Insufficient data for trend analysis'}
        
        recent = self.performance_history[-10:]  # Last 10 snapshots
        older = self.performance_history[-20:-10] if len(self.performance_history) >= 20 else []
        
        if not older:
            return {'message': 'Insufficient historical data'}
        
        # Calculate averages
        recent_avg = {
            'cache_hit_rate': sum(s.cache_hit_rate for s in recent) / len(recent),
            'error_rate': sum(s.error_rate for s in recent) / len(recent),
            'response_time': sum(s.avg_response_time for s in recent) / len(recent),
            'cost_per_request': sum(s.cost_per_request for s in recent) / len(recent)
        }
        
        older_avg = {
            'cache_hit_rate': sum(s.cache_hit_rate for s in older) / len(older),
            'error_rate': sum(s.error_rate for s in older) / len(older),
            'response_time': sum(s.avg_response_time for s in older) / len(older),
            'cost_per_request': sum(s.cost_per_request for s in older) / len(older)
        }
        
        # Calculate trends
        trends = {}
        for metric in recent_avg:
            change = recent_avg[metric] - older_avg[metric]
            percent_change = (change / max(older_avg[metric], 0.0001)) * 100
            trends[metric] = {
                'change': change,
                'percent_change': percent_change,
                'direction': 'improving' if (
                    (metric in ['cache_hit_rate'] and change > 0) or
                    (metric in ['error_rate', 'response_time', 'cost_per_request'] and change < 0)
                ) else 'degrading' if change != 0 else 'stable'
            }
        
        return trends
    
    def _analyze_cost_efficiency(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze cost efficiency and provide insights
        """
        total_cost = metrics.get('total_cost', 0.0)
        total_requests = metrics.get('total_requests', 0)
        
        if total_requests == 0:
            return {'message': 'No requests to analyze'}
        
        cost_per_request = total_cost / total_requests
        
        # Estimate potential savings
        cache_hit_rate = metrics.get('cache_hit_rate', 0.0)
        potential_cache_savings = (1 - cache_hit_rate) * total_cost * 0.8  # 80% savings from caching
        
        # Model optimization savings
        model_usage = metrics.get('model_usage_distribution', {})
        estimated_model_savings = 0.0
        
        for model, count in model_usage.items():
            if 'claude-3-opus' in model:
                # Could save by switching to Claude-3-Sonnet
                estimated_model_savings += count * 0.002  # Approximate savings per request
            elif 'claude-3-sonnet' in model:
                # Could save by switching to Claude-3-Haiku for simple tasks
                estimated_model_savings += count * 0.0015
        
        return {
            'current_cost_per_request': cost_per_request,
            'total_cost': total_cost,
            'potential_cache_savings': potential_cache_savings,
            'potential_model_savings': estimated_model_savings,
            'total_potential_savings': potential_cache_savings + estimated_model_savings,
            'cost_efficiency_score': max(0, 100 - (cost_per_request * 2000)),  # 100 = optimal
            'cost_breakdown': self._get_cost_breakdown(model_usage)
        }
    
    def _analyze_model_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze individual model performance
        """
        model_usage = metrics.get('model_usage_distribution', {})
        circuit_breakers = metrics.get('circuit_breaker_status', {})
        
        model_analysis = {}
        
        for model, usage_count in model_usage.items():
            # Get model config
            model_config = None
            for ai_model, config in ai_config.model_configs.items():
                if config.model_id == model:
                    model_config = config
                    break
            
            if model_config:
                failure_count = circuit_breakers.get(model, {}).get('failures', 0)
                reliability = max(0, 100 - (failure_count * 20))  # Each failure reduces reliability by 20%
                
                model_analysis[model] = {
                    'usage_count': usage_count,
                    'reliability_score': reliability,
                    'avg_cost_per_request': model_config.cost_per_1k_tokens,
                    'quality_score': model_config.quality_score,
                    'avg_response_time': model_config.avg_response_time_ms,
                    'recommended_use_cases': model_config.use_cases,
                    'performance_rating': self._calculate_model_rating(model_config, reliability)
                }
        
        return model_analysis
    
    def _get_top_model(self, metrics: Dict[str, Any]) -> str:
        """Get the most used model"""
        model_usage = metrics.get('model_usage_distribution', {})
        if not model_usage:
            return 'none'
        return max(model_usage.items(), key=lambda x: x[1])[0]
    
    def _get_cost_breakdown(self, model_usage: Dict[str, int]) -> Dict[str, float]:
        """Get cost breakdown by model"""
        breakdown = {}
        
        for model, count in model_usage.items():
            # Get model config
            for ai_model, config in ai_config.model_configs.items():
                if config.model_id == model:
                    estimated_cost = count * config.cost_per_1k_tokens
                    breakdown[model] = estimated_cost
                    break
        
        return breakdown
    
    def _calculate_model_rating(self, model_config: Any, reliability: float) -> str:
        """Calculate overall model performance rating"""
        # Weighted score considering quality, cost, speed, and reliability
        quality_norm = model_config.quality_score / 10.0
        cost_norm = 1.0 - (model_config.cost_per_1k_tokens / 0.005)  # Normalize to 0-1
        speed_norm = 1.0 - (model_config.avg_response_time_ms / 2000.0)
        reliability_norm = reliability / 100.0
        
        overall_score = (
            quality_norm * 0.3 +
            cost_norm * 0.2 +
            speed_norm * 0.2 +
            reliability_norm * 0.3
        ) * 100
        
        if overall_score >= 80:
            return 'EXCELLENT'
        elif overall_score >= 60:
            return 'GOOD'
        elif overall_score >= 40:
            return 'FAIR'
        else:
            return 'NEEDS_IMPROVEMENT'
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive AI performance report
        """
        metrics = await self.collect_real_time_metrics()
        
        return {
            'report_timestamp': datetime.utcnow().isoformat(),
            'executive_summary': self._generate_executive_summary(metrics),
            'detailed_metrics': metrics,
            'action_items': self._prioritize_action_items(metrics['recommendations']),
            'performance_grade': self._calculate_performance_grade(metrics['performance_scores']),
            'next_review_date': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
    
    def _generate_executive_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of AI performance"""
        current_metrics = metrics['current_metrics']
        performance_scores = metrics['performance_scores']
        
        return {
            'overall_health': 'EXCELLENT' if performance_scores['overall_score'] >= 80 else
                             'GOOD' if performance_scores['overall_score'] >= 60 else
                             'NEEDS_ATTENTION',
            'key_metrics': {
                'total_requests': current_metrics.get('total_requests', 0),
                'success_rate': f"{(1 - current_metrics.get('error_rate', 0)) * 100:.1f}%",
                'avg_response_time': f"{current_metrics.get('avg_response_time', 0):.2f}s",
                'cost_per_request': f"${current_metrics.get('cost_per_request', 0):.4f}"
            },
            'top_concerns': [alert['message'] for alert in metrics['alerts'] 
                           if alert['severity'] in ['CRITICAL', 'WARNING']],
            'optimization_potential': f"${metrics['cost_analysis'].get('total_potential_savings', 0):.2f}"
        }
    
    def _prioritize_action_items(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize action items by impact and effort"""
        # Sort by priority and estimated impact
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        
        return sorted(recommendations, 
                     key=lambda x: priority_order.get(x['priority'], 0), 
                     reverse=True)[:5]  # Top 5 action items
    
    def _calculate_performance_grade(self, scores: Dict[str, float]) -> str:
        """Calculate letter grade for overall performance"""
        overall_score = scores['overall_score']
        
        if overall_score >= 90:
            return 'A+'
        elif overall_score >= 85:
            return 'A'
        elif overall_score >= 80:
            return 'A-'
        elif overall_score >= 75:
            return 'B+'
        elif overall_score >= 70:
            return 'B'
        elif overall_score >= 65:
            return 'B-'
        elif overall_score >= 60:
            return 'C+'
        elif overall_score >= 55:
            return 'C'
        else:
            return 'D'


# Global instance
ai_monitor = AIPerformanceMonitor()
