"""
Circuit Breaker Health Check

Provides circuit breaker pattern for health checks and external service calls.
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
import logging

from .core import HealthCheckResult, HealthStatus, HealthCheckType

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation - requests allowed
    OPEN = "open"          # Failure state - requests blocked
    HALF_OPEN = "half_open"  # Testing state - limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    success_threshold: int = 3  # Number of successes needed to close from half-open
    timeout_seconds: int = 60   # How long to wait before trying half-open
    reset_timeout_seconds: int = 300  # How long to wait before full reset
    expected_exceptions: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_failures: int = 0
    current_successes: int = 0
    
    def failure_rate(self) -> float:
        """Calculate current failure rate"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    def success_rate(self) -> float:
        """Calculate current success rate"""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls


class CircuitBreakerHealthCheck:
    """
    Circuit breaker implementation for health checks and service calls
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.state_change_time = datetime.utcnow()
        
        # Metrics
        self.metrics = CircuitBreakerMetrics()
        
        # Callbacks
        self._on_state_change: Optional[Callable] = None
        self._fallback_function: Optional[Callable] = None
        
        logger.info(f"Circuit breaker '{name}' initialized in CLOSED state")
    
    def set_state_change_callback(self, callback: Callable[[str, CircuitBreakerState, CircuitBreakerState], None]):
        """Set callback for state changes"""
        self._on_state_change = callback
    
    def set_fallback_function(self, fallback: Callable):
        """Set fallback function for when circuit is open"""
        self._fallback_function = fallback
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function through the circuit breaker
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result or fallback result
            
        Raises:
            Exception if circuit is open and no fallback is available
        """
        # Check if circuit is open
        if self.state == CircuitBreakerState.OPEN:
            if not self._should_attempt_reset():
                if self._fallback_function:
                    logger.warning(f"Circuit breaker '{self.name}' is OPEN, using fallback")
                    return await self._call_fallback(*args, **kwargs)
                else:
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN and no fallback available")
            else:
                # Try half-open state
                self._transition_to_half_open()
        
        # Attempt to call the function
        try:
            start_time = time.time()
            
            # Call the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            duration = (time.time() - start_time) * 1000
            self._record_success(duration)
            
            return result
            
        except self.config.expected_exceptions as e:
            # Record failure
            duration = (time.time() - start_time) * 1000
            self._record_failure(e, duration)
            
            # Use fallback if available
            if self._fallback_function:
                logger.warning(f"Circuit breaker '{self.name}' failure, using fallback: {e}")
                return await self._call_fallback(*args, **kwargs)
            else:
                raise e
    
    async def health_check(self) -> HealthCheckResult:
        """Perform health check on the circuit breaker itself"""
        now = datetime.utcnow()
        
        # Calculate health based on state and metrics
        if self.state == CircuitBreakerState.CLOSED:
            status = HealthStatus.HEALTHY
            message = "Circuit breaker closed - normal operation"
        elif self.state == CircuitBreakerState.HALF_OPEN:
            status = HealthStatus.DEGRADED
            message = "Circuit breaker half-open - testing recovery"
        else:  # OPEN
            status = HealthStatus.UNHEALTHY
            message = f"Circuit breaker open - blocking requests"
        
        # Additional health indicators
        details = {
            'state': self.state.value,
            'failure_rate': round(self.metrics.failure_rate() * 100, 2),
            'success_rate': round(self.metrics.success_rate() * 100, 2),
            'total_calls': self.metrics.total_calls,
            'current_failures': self.metrics.current_failures,
            'current_successes': self.metrics.current_successes,
            'time_in_current_state': (now - self.state_change_time).total_seconds(),
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'success_threshold': self.config.success_threshold,
                'timeout_seconds': self.config.timeout_seconds
            }
        }
        
        if self.last_failure_time:
            details['last_failure'] = self.last_failure_time.isoformat() + 'Z'
            details['time_since_last_failure'] = (now - self.last_failure_time).total_seconds()
        
        if self.last_success_time:
            details['last_success'] = self.last_success_time.isoformat() + 'Z'
            details['time_since_last_success'] = (now - self.last_success_time).total_seconds()
        
        return HealthCheckResult(
            status=status,
            check_type=HealthCheckType.DEPENDENCY,
            service_name="circuit_breaker",
            check_name=self.name,
            message=message,
            details=details
        )
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        return self.state
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics"""
        return self.metrics
    
    def force_open(self):
        """Manually force circuit breaker to open state"""
        old_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.state_change_time = datetime.utcnow()
        self._notify_state_change(old_state, self.state)
        logger.warning(f"Circuit breaker '{self.name}' manually forced to OPEN state")
    
    def force_close(self):
        """Manually force circuit breaker to closed state"""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.state_change_time = datetime.utcnow()
        self.metrics.current_failures = 0
        self.metrics.current_successes = 0
        self._notify_state_change(old_state, self.state)
        logger.info(f"Circuit breaker '{self.name}' manually forced to CLOSED state")
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = CircuitBreakerMetrics()
        logger.info(f"Circuit breaker '{self.name}' metrics reset")
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open state"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.timeout_seconds
    
    def _transition_to_half_open(self):
        """Transition to half-open state"""
        old_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.state_change_time = datetime.utcnow()
        self.metrics.current_successes = 0
        self._notify_state_change(old_state, self.state)
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN state")
    
    def _record_success(self, duration_ms: float):
        """Record a successful call"""
        now = datetime.utcnow()
        self.last_success_time = now
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.current_successes += 1
        
        # Reset failure count on success
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.metrics.current_successes >= self.config.success_threshold:
                # Transition back to closed
                old_state = self.state
                self.state = CircuitBreakerState.CLOSED
                self.state_change_time = now
                self.metrics.current_failures = 0
                self._notify_state_change(old_state, self.state)
                logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED state after {self.metrics.current_successes} successes")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success in closed state
            self.metrics.current_failures = 0
    
    def _record_failure(self, exception: Exception, duration_ms: float):
        """Record a failed call"""
        now = datetime.utcnow()
        self.last_failure_time = now
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.current_failures += 1
        
        # Check if we should open the circuit
        if self.state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]:
            if self.metrics.current_failures >= self.config.failure_threshold:
                old_state = self.state
                self.state = CircuitBreakerState.OPEN
                self.state_change_time = now
                self._notify_state_change(old_state, self.state)
                logger.warning(f"Circuit breaker '{self.name}' transitioned to OPEN state after {self.metrics.current_failures} failures")
    
    async def _call_fallback(self, *args, **kwargs) -> Any:
        """Call the fallback function"""
        try:
            if asyncio.iscoroutinefunction(self._fallback_function):
                return await self._fallback_function(*args, **kwargs)
            else:
                return self._fallback_function(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback function failed for circuit breaker '{self.name}': {e}")
            raise e
    
    def _notify_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState):
        """Notify about state change"""
        transition = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'from_state': old_state.value,
            'to_state': new_state.value,
            'failure_count': self.metrics.current_failures,
            'success_count': self.metrics.current_successes
        }
        self.metrics.state_transitions.append(transition)
        
        if self._on_state_change:
            try:
                self._on_state_change(self.name, old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreakerHealthCheck] = {}
    
    def register(self, name: str, breaker: CircuitBreakerHealthCheck):
        """Register a circuit breaker"""
        self._breakers[name] = breaker
        logger.info(f"Circuit breaker '{name}' registered")
    
    def get(self, name: str) -> Optional[CircuitBreakerHealthCheck]:
        """Get a circuit breaker by name"""
        return self._breakers.get(name)
    
    def get_all(self) -> Dict[str, CircuitBreakerHealthCheck]:
        """Get all registered circuit breakers"""
        return self._breakers.copy()
    
    async def health_check_all(self) -> List[HealthCheckResult]:
        """Perform health check on all circuit breakers"""
        results = []
        for breaker in self._breakers.values():
            try:
                result = await breaker.health_check()
                results.append(result)
            except Exception as e:
                logger.error(f"Error checking circuit breaker health: {e}")
                results.append(HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    check_type=HealthCheckType.DEPENDENCY,
                    service_name="circuit_breaker",
                    check_name=breaker.name,
                    error=str(e),
                    message="Health check failed"
                ))
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all circuit breakers"""
        summary = {
            'total_breakers': len(self._breakers),
            'states': {state.value: 0 for state in CircuitBreakerState},
            'breakers': {}
        }
        
        for name, breaker in self._breakers.items():
            state = breaker.get_state()
            summary['states'][state.value] += 1
            summary['breakers'][name] = {
                'state': state.value,
                'failure_rate': round(breaker.metrics.failure_rate() * 100, 2),
                'total_calls': breaker.metrics.total_calls
            }
        
        return summary


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()
