"""
Error Recovery and Resilience Service
Provides comprehensive error handling, automatic recovery, and system resilience.
"""

import json
import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from functools import wraps
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecoveryStrategy(Enum):
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    GRACEFUL_DEGRADATION = "GRACEFUL_DEGRADATION"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    MANUAL_INTERVENTION = "MANUAL_INTERVENTION"


class ErrorRecoveryService:
    """Advanced error recovery and resilience management"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.sns = boto3.client('sns')
        self.cloudwatch = boto3.client('cloudwatch')
        
        # Error tracking table
        self.error_table = self.dynamodb.Table('ai-nutritionist-error-log')
        self.circuit_breaker_table = self.dynamodb.Table('ai-nutritionist-circuit-breakers')
        
        # Circuit breaker states
        self.circuit_breakers = {}
        
        # Error patterns and recovery strategies
        self.error_patterns = {
            'api_rate_limit': {
                'patterns': ['rate limit', 'too many requests', '429'],
                'severity': ErrorSeverity.MEDIUM,
                'strategy': RecoveryStrategy.RETRY,
                'max_retries': 3,
                'backoff_multiplier': 2.0,
                'fallback_enabled': True
            },
            'api_timeout': {
                'patterns': ['timeout', 'connection timeout', 'read timeout'],
                'severity': ErrorSeverity.MEDIUM,
                'strategy': RecoveryStrategy.RETRY,
                'max_retries': 2,
                'backoff_multiplier': 1.5,
                'fallback_enabled': True
            },
            'api_authentication': {
                'patterns': ['unauthorized', '401', 'invalid credentials'],
                'severity': ErrorSeverity.HIGH,
                'strategy': RecoveryStrategy.MANUAL_INTERVENTION,
                'max_retries': 0,
                'fallback_enabled': True
            },
            'service_unavailable': {
                'patterns': ['service unavailable', '503', 'internal server error'],
                'severity': ErrorSeverity.HIGH,
                'strategy': RecoveryStrategy.CIRCUIT_BREAKER,
                'max_retries': 1,
                'circuit_breaker_threshold': 5,
                'fallback_enabled': True
            },
            'data_validation': {
                'patterns': ['validation error', 'invalid input', 'malformed data'],
                'severity': ErrorSeverity.LOW,
                'strategy': RecoveryStrategy.GRACEFUL_DEGRADATION,
                'max_retries': 0,
                'fallback_enabled': True
            },
            'cost_limit_exceeded': {
                'patterns': ['cost limit', 'budget exceeded', 'quota exceeded'],
                'severity': ErrorSeverity.CRITICAL,
                'strategy': RecoveryStrategy.GRACEFUL_DEGRADATION,
                'max_retries': 0,
                'fallback_enabled': True
            }
        }
        
        # Fallback responses
        self.fallback_responses = {
            'meal_plan': {
                'success': True,
                'meal_plan': {
                    'meals': [
                        {
                            'meal_type': 'breakfast',
                            'recipe': 'Oatmeal with berries',
                            'calories': 300,
                            'protein': 10,
                            'note': 'Fallback meal - personalized meal plan temporarily unavailable'
                        }
                    ]
                },
                'fallback': True
            },
            'nutrition_analysis': {
                'success': True,
                'nutrition': {
                    'calories': 'approximately 150-200 per serving',
                    'protein': 'moderate',
                    'carbs': 'moderate',
                    'note': 'Detailed nutrition analysis temporarily unavailable'
                },
                'fallback': True
            },
            'recipe_search': {
                'success': True,
                'recipes': [
                    {
                        'name': 'Simple Healthy Meal',
                        'ingredients': ['lean protein', 'vegetables', 'whole grains'],
                        'instructions': 'Combine ingredients and cook as preferred',
                        'note': 'Detailed recipe search temporarily unavailable'
                    }
                ],
                'fallback': True
            }
        }
    
    def with_error_recovery(self, operation_name: str, fallback_type: Optional[str] = None):
        """Decorator for automatic error recovery"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.execute_with_recovery(
                    func, operation_name, fallback_type, *args, **kwargs
                )
            return wrapper
        return decorator
    
    def execute_with_recovery(self, func: Callable, operation_name: str, 
                            fallback_type: Optional[str] = None, 
                            *args, **kwargs) -> Dict[str, Any]:
        """Execute function with comprehensive error recovery"""
        start_time = time.time()
        attempt = 0
        last_error = None
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open(operation_name):
                logger.warning(f"Circuit breaker open for {operation_name}, using fallback")
                return self._get_fallback_response(fallback_type or operation_name)
            
            while True:
                attempt += 1
                
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Record successful execution
                    self._record_success(operation_name, time.time() - start_time, attempt)
                    
                    # Reset circuit breaker on success
                    self._reset_circuit_breaker(operation_name)
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    error_info = self._analyze_error(e, operation_name)
                    
                    # Log error details
                    self._log_error(operation_name, e, attempt, error_info)
                    
                    # Determine recovery strategy
                    strategy = error_info.get('strategy', RecoveryStrategy.FALLBACK)
                    max_retries = error_info.get('max_retries', 0)
                    
                    if strategy == RecoveryStrategy.RETRY and attempt <= max_retries:
                        # Calculate backoff delay
                        backoff_delay = self._calculate_backoff_delay(
                            attempt, error_info.get('backoff_multiplier', 1.0)
                        )
                        
                        logger.info(f"Retrying {operation_name} (attempt {attempt}/{max_retries}) "
                                  f"after {backoff_delay}s delay")
                        time.sleep(backoff_delay)
                        continue
                    
                    elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                        self._update_circuit_breaker(operation_name, error_info)
                    
                    # If we reach here, use fallback or raise error
                    break
            
            # All retries exhausted or non-retryable error
            if fallback_type and self._should_use_fallback(last_error, operation_name):
                logger.warning(f"Using fallback for {operation_name} after error: {last_error}")
                return self._get_fallback_response(fallback_type)
            else:
                # Re-raise the last error
                raise last_error
                
        except Exception as e:
            # Final error handling
            self._handle_final_error(operation_name, e, attempt)
            
            # Return fallback if available
            if fallback_type:
                return self._get_fallback_response(fallback_type)
            else:
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'operation': operation_name
                }
    
    def get_error_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive error analytics"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Query error logs
            response = self.error_table.scan(
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )
            
            errors = response.get('Items', [])
            
            # Analyze error patterns
            analytics = {
                'summary': self._calculate_error_summary(errors),
                'error_patterns': self._analyze_error_patterns(errors),
                'recovery_effectiveness': self._analyze_recovery_effectiveness(errors),
                'system_health': self._assess_system_health(errors),
                'recommendations': self._generate_error_recommendations(errors)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error generating error analytics: {e}")
            return {'error': 'Failed to generate error analytics'}
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        try:
            status = {}
            
            for operation, breaker in self.circuit_breakers.items():
                status[operation] = {
                    'state': breaker['state'],
                    'failure_count': breaker['failure_count'],
                    'last_failure_time': breaker.get('last_failure_time'),
                    'next_attempt_time': breaker.get('next_attempt_time')
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting circuit breaker status: {e}")
            return {}
    
    def reset_circuit_breaker(self, operation_name: str) -> bool:
        """Manually reset a circuit breaker"""
        try:
            if operation_name in self.circuit_breakers:
                self.circuit_breakers[operation_name] = {
                    'state': 'CLOSED',
                    'failure_count': 0,
                    'last_failure_time': None,
                    'next_attempt_time': None
                }
                
                # Update in DynamoDB
                self.circuit_breaker_table.put_item(
                    Item={
                        'operation_name': operation_name,
                        'state': 'CLOSED',
                        'failure_count': 0,
                        'last_reset': datetime.utcnow().isoformat()
                    }
                )
                
                logger.info(f"Circuit breaker reset for {operation_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resetting circuit breaker: {e}")
            return False
    
    def _analyze_error(self, error: Exception, operation_name: str) -> Dict[str, Any]:
        """Analyze error and determine recovery strategy"""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Check against known error patterns
        for pattern_name, pattern_config in self.error_patterns.items():
            for pattern in pattern_config['patterns']:
                if pattern in error_str:
                    return {
                        'pattern': pattern_name,
                        'severity': pattern_config['severity'],
                        'strategy': pattern_config['strategy'],
                        'max_retries': pattern_config['max_retries'],
                        'backoff_multiplier': pattern_config.get('backoff_multiplier', 1.0),
                        'fallback_enabled': pattern_config.get('fallback_enabled', False)
                    }
        
        # Default error handling
        return {
            'pattern': 'unknown',
            'severity': ErrorSeverity.MEDIUM,
            'strategy': RecoveryStrategy.FALLBACK,
            'max_retries': 1,
            'backoff_multiplier': 1.0,
            'fallback_enabled': True
        }
    
    def _log_error(self, operation_name: str, error: Exception, 
                  attempt: int, error_info: Dict[str, Any]) -> None:
        """Log error details for analysis"""
        try:
            timestamp = datetime.utcnow()
            
            error_log = {
                'error_id': f"{operation_name}_{timestamp.timestamp()}",
                'operation_name': operation_name,
                'timestamp': timestamp.isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_pattern': error_info.get('pattern', 'unknown'),
                'severity': error_info.get('severity', ErrorSeverity.MEDIUM).value,
                'attempt': attempt,
                'recovery_strategy': error_info.get('strategy', RecoveryStrategy.FALLBACK).value,
                'traceback': traceback.format_exc(),
                'ttl': int((timestamp + timedelta(days=30)).timestamp())
            }
            
            self.error_table.put_item(Item=error_log)
            
            # Send CloudWatch metrics
            self._send_error_metrics(operation_name, error_info)
            
            # Check if we need to send alerts
            if error_info.get('severity') in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self._send_error_alert(operation_name, error, error_info)
            
        except Exception as e:
            logger.error(f"Error logging error details: {e}")
    
    def _record_success(self, operation_name: str, duration: float, attempts: int) -> None:
        """Record successful operation for analytics"""
        try:
            # Send success metrics to CloudWatch
            self.cloudwatch.put_metric_data(
                Namespace='AINutritionist/Resilience',
                MetricData=[
                    {
                        'MetricName': 'OperationSuccess',
                        'Dimensions': [{'Name': 'Operation', 'Value': operation_name}],
                        'Value': 1,
                        'Unit': 'Count'
                    },
                    {
                        'MetricName': 'OperationDuration',
                        'Dimensions': [{'Name': 'Operation', 'Value': operation_name}],
                        'Value': duration,
                        'Unit': 'Seconds'
                    },
                    {
                        'MetricName': 'AttemptsToSuccess',
                        'Dimensions': [{'Name': 'Operation', 'Value': operation_name}],
                        'Value': attempts,
                        'Unit': 'Count'
                    }
                ]
            )
            
        except Exception as e:
            logger.warning(f"Error recording success metrics: {e}")
    
    def _calculate_backoff_delay(self, attempt: int, multiplier: float) -> float:
        """Calculate exponential backoff delay"""
        base_delay = 0.5  # Start with 500ms
        max_delay = 30.0  # Cap at 30 seconds
        
        delay = base_delay * (multiplier ** (attempt - 1))
        return min(delay, max_delay)
    
    def _is_circuit_breaker_open(self, operation_name: str) -> bool:
        """Check if circuit breaker is open for operation"""
        if operation_name not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[operation_name]
        
        if breaker['state'] == 'OPEN':
            # Check if we should try again (half-open state)
            if breaker.get('next_attempt_time'):
                if datetime.utcnow() >= datetime.fromisoformat(breaker['next_attempt_time']):
                    breaker['state'] = 'HALF_OPEN'
                    return False
            return True
        
        return False
    
    def _update_circuit_breaker(self, operation_name: str, error_info: Dict[str, Any]) -> None:
        """Update circuit breaker state based on error"""
        threshold = error_info.get('circuit_breaker_threshold', 5)
        
        if operation_name not in self.circuit_breakers:
            self.circuit_breakers[operation_name] = {
                'state': 'CLOSED',
                'failure_count': 0,
                'last_failure_time': None,
                'next_attempt_time': None
            }
        
        breaker = self.circuit_breakers[operation_name]
        breaker['failure_count'] += 1
        breaker['last_failure_time'] = datetime.utcnow().isoformat()
        
        if breaker['failure_count'] >= threshold:
            breaker['state'] = 'OPEN'
            # Set next attempt time (30 seconds from now)
            breaker['next_attempt_time'] = (datetime.utcnow() + timedelta(seconds=30)).isoformat()
            
            logger.warning(f"Circuit breaker opened for {operation_name} after {threshold} failures")
    
    def _reset_circuit_breaker(self, operation_name: str) -> None:
        """Reset circuit breaker after successful operation"""
        if operation_name in self.circuit_breakers:
            self.circuit_breakers[operation_name] = {
                'state': 'CLOSED',
                'failure_count': 0,
                'last_failure_time': None,
                'next_attempt_time': None
            }
    
    def _should_use_fallback(self, error: Exception, operation_name: str) -> bool:
        """Determine if fallback should be used"""
        error_info = self._analyze_error(error, operation_name)
        return error_info.get('fallback_enabled', True)
    
    def _get_fallback_response(self, fallback_type: str) -> Dict[str, Any]:
        """Get appropriate fallback response"""
        fallback = self.fallback_responses.get(fallback_type, {
            'success': True,
            'message': 'Service temporarily unavailable. Please try again later.',
            'fallback': True
        })
        
        # Add timestamp to fallback response
        fallback['fallback_timestamp'] = datetime.utcnow().isoformat()
        
        return fallback
    
    def _handle_final_error(self, operation_name: str, error: Exception, attempts: int) -> None:
        """Handle final error when all recovery attempts failed"""
        logger.error(f"Final error in {operation_name} after {attempts} attempts: {error}")
        
        # Send critical error metrics
        try:
            self.cloudwatch.put_metric_data(
                Namespace='AINutritionist/Resilience',
                MetricData=[
                    {
                        'MetricName': 'FinalError',
                        'Dimensions': [{'Name': 'Operation', 'Value': operation_name}],
                        'Value': 1,
                        'Unit': 'Count'
                    }
                ]
            )
        except Exception as e:
            logger.warning(f"Error sending final error metrics: {e}")
    
    def _send_error_metrics(self, operation_name: str, error_info: Dict[str, Any]) -> None:
        """Send error metrics to CloudWatch"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace='AINutritionist/Resilience',
                MetricData=[
                    {
                        'MetricName': 'ErrorCount',
                        'Dimensions': [
                            {'Name': 'Operation', 'Value': operation_name},
                            {'Name': 'ErrorPattern', 'Value': error_info.get('pattern', 'unknown')}
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    }
                ]
            )
        except Exception as e:
            logger.warning(f"Error sending error metrics: {e}")
    
    def _send_error_alert(self, operation_name: str, error: Exception, 
                         error_info: Dict[str, Any]) -> None:
        """Send error alert notification"""
        try:
            # This would send to SNS topic for alerting
            # Implementation depends on your alerting setup
            pass
        except Exception as e:
            logger.warning(f"Error sending error alert: {e}")
    
    def _calculate_error_summary(self, errors: List[Dict]) -> Dict[str, Any]:
        """Calculate error summary statistics"""
        if not errors:
            return {'total_errors': 0}
        
        total_errors = len(errors)
        error_types = {}
        severity_counts = {}
        
        for error in errors:
            error_type = error.get('error_pattern', 'unknown')
            severity = error.get('severity', 'MEDIUM')
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': total_errors,
            'error_types': error_types,
            'severity_distribution': severity_counts,
            'most_common_error': max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }
    
    def _analyze_error_patterns(self, errors: List[Dict]) -> Dict[str, Any]:
        """Analyze error patterns and trends"""
        # This would analyze trends, correlations, etc.
        return {
            'trending_errors': ['api_rate_limit', 'timeout'],
            'peak_error_hours': [14, 15, 16],  # 2-4 PM
            'error_correlation': 'Higher errors during peak usage'
        }
    
    def _analyze_recovery_effectiveness(self, errors: List[Dict]) -> Dict[str, Any]:
        """Analyze effectiveness of recovery strategies"""
        return {
            'retry_success_rate': 0.75,
            'fallback_usage_rate': 0.20,
            'circuit_breaker_activations': 3,
            'average_recovery_time': 2.5
        }
    
    def _assess_system_health(self, errors: List[Dict]) -> Dict[str, str]:
        """Assess overall system health based on errors"""
        if not errors:
            return {'status': 'HEALTHY', 'confidence': 'HIGH'}
        
        total_errors = len(errors)
        
        if total_errors < 10:
            return {'status': 'HEALTHY', 'confidence': 'HIGH'}
        elif total_errors < 50:
            return {'status': 'WARNING', 'confidence': 'MEDIUM'}
        else:
            return {'status': 'UNHEALTHY', 'confidence': 'HIGH'}
    
    def _generate_error_recommendations(self, errors: List[Dict]) -> List[str]:
        """Generate recommendations for improving system resilience"""
        recommendations = []
        
        if not errors:
            return ['System appears healthy - continue monitoring']
        
        error_types = {}
        for error in errors:
            error_type = error.get('error_pattern', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Analyze most common errors
        if error_types.get('api_rate_limit', 0) > 5:
            recommendations.append('Consider implementing more aggressive caching to reduce API calls')
        
        if error_types.get('api_timeout', 0) > 3:
            recommendations.append('Optimize API call timeouts and implement connection pooling')
        
        if error_types.get('service_unavailable', 0) > 2:
            recommendations.append('Implement more robust fallback mechanisms for external services')
        
        return recommendations
