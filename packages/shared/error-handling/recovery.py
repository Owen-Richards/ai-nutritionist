"""
Error Recovery Management

Provides intelligent error recovery strategies, circuit breakers,
and system resilience patterns.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List, Union
from enum import Enum
from dataclasses import dataclass, field

from .exceptions import BaseError, InfrastructureError, ErrorSeverity
from .metrics import ErrorMetricsCollector

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    QUEUE_FOR_LATER = "queue_for_later"
    ALERT_AND_CONTINUE = "alert_and_continue"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RecoveryConfig:
    """Configuration for error recovery"""
    strategy: RecoveryStrategy
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    timeout_seconds: int = 30
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    fallback_function: Optional[Callable] = None
    enable_metrics: bool = True


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation"""
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0


@dataclass
class ErrorPattern:
    """Error pattern for intelligent recovery"""
    error_type: str
    patterns: List[str] = field(default_factory=list)
    recovery_config: RecoveryConfig = field(default_factory=lambda: RecoveryConfig(RecoveryStrategy.RETRY))
    priority: int = 1


class ErrorRecoveryManager:
    """
    Comprehensive error recovery management system
    
    Provides intelligent error recovery with multiple strategies,
    circuit breakers, and adaptive behavior based on error patterns.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics_collector = ErrorMetricsCollector()
        
        # Default error patterns and recovery strategies
        self.error_patterns = {
            'rate_limit': ErrorPattern(
                error_type='rate_limit',
                patterns=['rate limit', 'too many requests', '429'],
                recovery_config=RecoveryConfig(
                    strategy=RecoveryStrategy.RETRY,
                    max_retries=3,
                    base_delay=60.0,
                    max_delay=300.0,
                    backoff_multiplier=1.5
                )
            ),
            'timeout': ErrorPattern(
                error_type='timeout',
                patterns=['timeout', 'connection timeout', 'read timeout'],
                recovery_config=RecoveryConfig(
                    strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                    max_retries=2,
                    circuit_breaker_threshold=3
                )
            ),
            'service_unavailable': ErrorPattern(
                error_type='service_unavailable',
                patterns=['service unavailable', '503', 'temporarily unavailable'],
                recovery_config=RecoveryConfig(
                    strategy=RecoveryStrategy.FALLBACK,
                    max_retries=1
                )
            ),
            'validation_error': ErrorPattern(
                error_type='validation_error',
                patterns=['validation error', 'invalid input', 'malformed'],
                recovery_config=RecoveryConfig(
                    strategy=RecoveryStrategy.ALERT_AND_CONTINUE,
                    max_retries=0
                )
            ),
            'authentication_error': ErrorPattern(
                error_type='authentication_error',
                patterns=['unauthorized', '401', 'authentication failed'],
                recovery_config=RecoveryConfig(
                    strategy=RecoveryStrategy.ALERT_AND_CONTINUE,
                    max_retries=0
                )
            ),
            'payment_error': ErrorPattern(
                error_type='payment_error',
                patterns=['payment failed', 'card declined', 'insufficient funds'],
                recovery_config=RecoveryConfig(
                    strategy=RecoveryStrategy.QUEUE_FOR_LATER,
                    max_retries=1
                )
            )
        }
        
        # Fallback responses for different scenarios
        self.fallback_responses = {
            'meal_plan': {
                'success': True,
                'message': 'Here\'s a basic meal plan to get you started!',
                'meal_plan': {
                    'meals': [
                        {
                            'meal_type': 'breakfast',
                            'name': 'Oatmeal with Berries',
                            'calories': 300,
                            'protein': 10,
                            'carbs': 45,
                            'fat': 8
                        },
                        {
                            'meal_type': 'lunch',
                            'name': 'Grilled Chicken Salad',
                            'calories': 400,
                            'protein': 35,
                            'carbs': 15,
                            'fat': 20
                        },
                        {
                            'meal_type': 'dinner',
                            'name': 'Salmon with Vegetables',
                            'calories': 450,
                            'protein': 40,
                            'carbs': 20,
                            'fat': 25
                        }
                    ]
                }
            },
            'nutrition_advice': {
                'success': True,
                'message': 'Focus on balanced nutrition with plenty of vegetables, lean proteins, and whole grains.',
                'advice': [
                    'Eat 5-7 servings of fruits and vegetables daily',
                    'Include lean protein with each meal',
                    'Choose whole grains over refined carbohydrates',
                    'Stay hydrated with 8+ glasses of water daily',
                    'Limit processed foods and added sugars'
                ]
            },
            'health_tracking': {
                'success': True,
                'message': 'Your health data is temporarily unavailable, but keep up the great work!',
                'recommendation': 'Continue following your established routine and check back later.'
            }
        }
    
    async def execute_with_recovery(
        self,
        func: Callable,
        operation_name: str,
        *args,
        fallback_type: Optional[str] = None,
        custom_config: Optional[RecoveryConfig] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute function with comprehensive error recovery
        
        Args:
            func: Function to execute
            operation_name: Name for logging and metrics
            fallback_type: Type of fallback response to use
            custom_config: Custom recovery configuration
            *args, **kwargs: Arguments for the function
        
        Returns:
            Result dictionary with success status and data/error info
        """
        start_time = time.time()
        attempt = 0
        last_error = None
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open(operation_name):
                logger.warning(f"Circuit breaker open for {operation_name}, using fallback")
                return self._get_fallback_response(fallback_type or operation_name)
            
            # Determine recovery strategy
            recovery_config = custom_config or self._get_recovery_config(operation_name)
            
            while attempt <= recovery_config.max_retries:
                attempt += 1
                
                try:
                    # Execute with timeout if specified
                    if recovery_config.timeout_seconds > 0:
                        result = await asyncio.wait_for(
                            self._execute_function(func, *args, **kwargs),
                            timeout=recovery_config.timeout_seconds
                        )
                    else:
                        result = await self._execute_function(func, *args, **kwargs)
                    
                    # Success - record metrics and reset circuit breaker
                    self._record_success(operation_name, time.time() - start_time, attempt)
                    self._reset_circuit_breaker(operation_name)
                    
                    return {
                        'success': True,
                        'data': result,
                        'attempts': attempt,
                        'execution_time': time.time() - start_time
                    }
                    
                except Exception as e:
                    last_error = e
                    
                    # Analyze error and determine recovery strategy
                    error_analysis = self._analyze_error(e, operation_name)
                    strategy = error_analysis.get('strategy', recovery_config.strategy)
                    
                    # Log error
                    self._log_error(operation_name, e, attempt, error_analysis)
                    
                    # Handle based on strategy
                    if strategy == RecoveryStrategy.RETRY and attempt <= recovery_config.max_retries:
                        delay = self._calculate_backoff_delay(attempt, recovery_config)
                        logger.info(
                            f"Retrying {operation_name} (attempt {attempt}/{recovery_config.max_retries}) "
                            f"after {delay:.2f}s delay"
                        )
                        await asyncio.sleep(delay)
                        continue
                        
                    elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                        self._update_circuit_breaker(operation_name, error_analysis)
                        
                    elif strategy == RecoveryStrategy.FALLBACK:
                        logger.warning(f"Using fallback for {operation_name}: {e}")
                        return self._get_fallback_response(fallback_type or operation_name)
                        
                    elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                        return self._get_degraded_response(operation_name, e)
                        
                    elif strategy == RecoveryStrategy.QUEUE_FOR_LATER:
                        await self._queue_for_later(operation_name, func, args, kwargs)
                        return {
                            'success': False,
                            'queued': True,
                            'message': 'Request queued for later processing',
                            'error': str(e)
                        }
                    
                    # If we reach here, stop retrying
                    break
            
            # All strategies exhausted
            return {
                'success': False,
                'error': str(last_error),
                'error_type': type(last_error).__name__,
                'attempts': attempt,
                'execution_time': time.time() - start_time,
                'fallback_available': fallback_type is not None
            }
            
        except Exception as e:
            # Final error handling
            self._handle_final_error(operation_name, e, attempt)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'attempts': attempt,
                'execution_time': time.time() - start_time
            }
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with proper async handling"""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _analyze_error(self, error: Exception, operation_name: str) -> Dict[str, Any]:
        """Analyze error to determine recovery strategy"""
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Check against known patterns
        for pattern_name, pattern in self.error_patterns.items():
            if any(p in error_message for p in pattern.patterns):
                return {
                    'pattern': pattern_name,
                    'strategy': pattern.recovery_config.strategy,
                    'severity': ErrorSeverity.HIGH if 'timeout' in pattern_name else ErrorSeverity.MEDIUM,
                    'max_retries': pattern.recovery_config.max_retries,
                    'backoff_multiplier': pattern.recovery_config.backoff_multiplier
                }
        
        # Default analysis
        if 'timeout' in error_message or 'connection' in error_message:
            return {
                'pattern': 'connection_issue',
                'strategy': RecoveryStrategy.CIRCUIT_BREAKER,
                'severity': ErrorSeverity.HIGH,
                'max_retries': 2,
                'backoff_multiplier': 2.0
            }
        elif '5' in error_type or 'server' in error_message:
            return {
                'pattern': 'server_error',
                'strategy': RecoveryStrategy.RETRY,
                'severity': ErrorSeverity.HIGH,
                'max_retries': 3,
                'backoff_multiplier': 1.5
            }
        else:
            return {
                'pattern': 'unknown',
                'strategy': RecoveryStrategy.FALLBACK,
                'severity': ErrorSeverity.MEDIUM,
                'max_retries': 1,
                'backoff_multiplier': 1.0
            }
    
    def _get_recovery_config(self, operation_name: str) -> RecoveryConfig:
        """Get recovery configuration for operation"""
        # Return default config - could be customized based on operation
        return RecoveryConfig(
            strategy=RecoveryStrategy.RETRY,
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0
        )
    
    def _calculate_backoff_delay(self, attempt: int, config: RecoveryConfig) -> float:
        """Calculate exponential backoff delay with jitter"""
        import random
        
        delay = min(
            config.base_delay * (config.backoff_multiplier ** (attempt - 1)),
            config.max_delay
        )
        
        # Add jitter (±25%)
        jitter = delay * 0.25 * (random.random() - 0.5) * 2
        return max(0.1, delay + jitter)
    
    def _is_circuit_breaker_open(self, operation_name: str) -> bool:
        """Check if circuit breaker is open for operation"""
        if operation_name not in self.circuit_breakers:
            return False
            
        breaker = self.circuit_breakers[operation_name]
        
        if breaker.state == CircuitBreakerState.CLOSED:
            return False
        elif breaker.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if breaker.last_failure_time and \
               (datetime.utcnow() - breaker.last_failure_time).total_seconds() >= breaker.recovery_timeout:
                breaker.state = CircuitBreakerState.HALF_OPEN
                return False
            return True
        else:  # HALF_OPEN
            return False
    
    def _update_circuit_breaker(self, operation_name: str, error_info: Dict[str, Any]):
        """Update circuit breaker state after error"""
        if operation_name not in self.circuit_breakers:
            self.circuit_breakers[operation_name] = CircuitBreaker(name=operation_name)
        
        breaker = self.circuit_breakers[operation_name]
        breaker.failure_count += 1
        breaker.last_failure_time = datetime.utcnow()
        breaker.total_requests += 1
        
        if breaker.failure_count >= breaker.failure_threshold:
            breaker.state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker opened for {operation_name} "
                f"after {breaker.failure_count} failures"
            )
    
    def _reset_circuit_breaker(self, operation_name: str):
        """Reset circuit breaker after successful operation"""
        if operation_name in self.circuit_breakers:
            breaker = self.circuit_breakers[operation_name]
            breaker.failure_count = 0
            breaker.state = CircuitBreakerState.CLOSED
            breaker.last_success_time = datetime.utcnow()
            breaker.successful_requests += 1
            breaker.total_requests += 1
    
    def _get_fallback_response(self, fallback_type: str) -> Dict[str, Any]:
        """Get appropriate fallback response"""
        if fallback_type in self.fallback_responses:
            response = self.fallback_responses[fallback_type].copy()
            response['fallback'] = True
            response['timestamp'] = datetime.utcnow().isoformat()
            return response
        
        return {
            'success': True,
            'fallback': True,
            'message': 'Service temporarily unavailable, using cached response',
            'data': {},
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_degraded_response(self, operation_name: str, error: Exception) -> Dict[str, Any]:
        """Get degraded service response"""
        return {
            'success': True,
            'degraded': True,
            'message': 'Service running in degraded mode',
            'limitations': ['Some features may be unavailable', 'Responses may be delayed'],
            'error_summary': str(error),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _queue_for_later(self, operation_name: str, func: Callable, args: tuple, kwargs: dict):
        """Queue failed operation for later retry"""
        # In a real implementation, this would use a message queue like SQS
        logger.info(f"Queuing {operation_name} for later processing")
        
        # Store in memory queue for now (would be persistent in production)
        queue_item = {
            'operation_name': operation_name,
            'function': func.__name__,
            'args': args,
            'kwargs': kwargs,
            'queued_at': datetime.utcnow().isoformat(),
            'retry_count': 0
        }
        
        # Would implement actual queueing logic here
        pass
    
    def _record_success(self, operation_name: str, execution_time: float, attempts: int):
        """Record successful operation metrics"""
        self.metrics_collector.record_success(operation_name, execution_time, attempts)
    
    def _log_error(self, operation_name: str, error: Exception, attempt: int, error_info: Dict[str, Any]):
        """Log error with context"""
        log_data = {
            'operation': operation_name,
            'attempt': attempt,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_info': error_info,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        severity = error_info.get('severity', ErrorSeverity.MEDIUM)
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"Error in {operation_name}: {error}", extra=log_data)
        else:
            logger.warning(f"Error in {operation_name}: {error}", extra=log_data)
    
    def _handle_final_error(self, operation_name: str, error: Exception, attempts: int):
        """Handle final error when all recovery attempts failed"""
        logger.error(f"Final error in {operation_name} after {attempts} attempts: {error}")
        
        # Send critical alert for repeated failures
        if attempts > 1:
            self.metrics_collector.record_critical_failure(operation_name, error, attempts)
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        status = {}
        for name, breaker in self.circuit_breakers.items():
            status[name] = {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'total_requests': breaker.total_requests,
                'success_rate': (
                    breaker.successful_requests / breaker.total_requests 
                    if breaker.total_requests > 0 else 0
                ),
                'last_failure_time': (
                    breaker.last_failure_time.isoformat() 
                    if breaker.last_failure_time else None
                ),
                'last_success_time': (
                    breaker.last_success_time.isoformat() 
                    if breaker.last_success_time else None
                )
            }
        return status
    
    def add_error_pattern(self, name: str, pattern: ErrorPattern):
        """Add custom error pattern"""
        self.error_patterns[name] = pattern
    
    def add_fallback_response(self, name: str, response: Dict[str, Any]):
        """Add custom fallback response"""
        self.fallback_responses[name] = response
