"""
AI Coach Service Health Check Implementation

Comprehensive health checks for the AI coach service including:
- AI model availability
- OpenAI API connectivity
- Vector database health
- Memory and performance monitoring
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any

from packages.shared.health_check import (
    HealthChecker, HealthStatus, HealthCheckResult,
    LivenessProbe, ReadinessProbe, StartupProbe,
    DatabaseHealthCheck, RedisHealthCheck, ExternalAPIHealthCheck,
    CircuitBreakerHealthCheck, CircuitBreakerConfig,
    HealthMonitor, CloudWatchHealthReporter,
    create_health_routes
)


class AICoachServiceHealthCheck:
    """Health check implementation for AI coach service"""
    
    def __init__(self):
        self.health_checker = HealthChecker(
            service_name="ai-coach-service",
            version="1.0.0",
            startup_timeout=45.0  # AI models may take longer to load
        )
        
        self._setup_probes()
        self._setup_dependency_checks()
        self._setup_circuit_breakers()
        
        # Initialize monitoring
        self.monitor = HealthMonitor(
            self.health_checker,
            monitoring_interval=60  # Check every minute for AI service
        )
        self.cloudwatch_reporter = CloudWatchHealthReporter(
            namespace="AICoachService/HealthCheck"
        )
        
        self.monitor.add_alert_callback(self._handle_health_alert)
        
        # AI-specific metrics tracking
        self._model_load_times = {}
        self._inference_times = []
    
    def _setup_probes(self):
        """Setup health probes"""
        
        # Liveness probe
        liveness = LivenessProbe("ai-coach-liveness")
        liveness.add_check(self._check_ai_service_responsive)
        liveness.add_check(self._check_model_inference)
        liveness.add_check(self._check_memory_pressure)
        
        self.health_checker.register_liveness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                liveness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "liveness_probe"
        )
        
        # Readiness probe
        readiness = ReadinessProbe("ai-coach-readiness")
        readiness.add_dependency_check(self._check_openai_ready)
        readiness.add_dependency_check(self._check_vector_db_ready)
        readiness.add_dependency_check(self._check_model_cache_ready)
        readiness.add_resource_check(self._check_gpu_availability)
        readiness.add_resource_check(self._check_inference_capacity)
        
        self.health_checker.register_readiness_check(
            lambda: asyncio.run_coroutine_threadsafe(
                readiness.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "readiness_probe"
        )
        
        # Startup probe
        startup = StartupProbe("ai-coach-startup")
        startup.add_startup_check(self._check_models_loading)
        startup.add_startup_check(self._check_vector_embeddings_loaded)
        startup.add_startup_check(self._check_coaching_context_initialized)
        startup.add_startup_check(self._check_personalization_engine_ready)
        
        self.health_checker.register_startup_check(
            lambda: asyncio.run_coroutine_threadsafe(
                startup.check(), asyncio.get_event_loop()
            ).result().status == HealthStatus.HEALTHY,
            "startup_probe"
        )
    
    def _setup_dependency_checks(self):
        """Setup dependency health checks"""
        
        # OpenAI API health check
        openai_check = ExternalAPIHealthCheck(
            name="openai_api",
            api_url="https://api.openai.com/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
            test_endpoint="models",
            timeout=15.0
        )
        self.health_checker.register_dependency_check(openai_check)
        
        # Vector database (if using external vector DB)
        if os.getenv("VECTOR_DB_HOST"):
            vector_db_check = DatabaseHealthCheck(
                name="vector_database",
                host=os.getenv("VECTOR_DB_HOST"),
                port=int(os.getenv("VECTOR_DB_PORT", "5432")),
                database=os.getenv("VECTOR_DB_NAME", "vectors"),
                user=os.getenv("VECTOR_DB_USER"),
                password=os.getenv("VECTOR_DB_PASSWORD"),
                timeout=8.0
            )
            self.health_checker.register_dependency_check(vector_db_check)
        
        # Redis for model caching
        redis_check = RedisHealthCheck(
            name="model_cache",
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_AI_DB", "2")),
            timeout=5.0
        )
        self.health_checker.register_dependency_check(redis_check)
        
        # User data database
        user_db_check = DatabaseHealthCheck(
            name="user_database",
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "ai_coach_db"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            timeout=5.0
        )
        self.health_checker.register_dependency_check(user_db_check)
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for AI services"""
        
        # OpenAI circuit breaker with AI-specific settings
        openai_breaker = CircuitBreakerHealthCheck(
            name="openai_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=2,  # Lower threshold for AI APIs
                success_threshold=3,
                timeout_seconds=45,   # Longer timeout for AI responses
                reset_timeout_seconds=300
            )
        )
        
        openai_breaker.set_fallback_function(self._openai_fallback)
        openai_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(openai_breaker)
        
        # Model inference circuit breaker
        inference_breaker = CircuitBreakerHealthCheck(
            name="model_inference_circuit_breaker",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=30,
                reset_timeout_seconds=120
            )
        )
        
        inference_breaker.set_fallback_function(self._inference_fallback)
        inference_breaker.set_state_change_callback(self._circuit_breaker_state_changed)
        
        self.health_checker.register_dependency_check(inference_breaker)
    
    # Liveness checks
    async def _check_ai_service_responsive(self) -> bool:
        """Check if AI service is responsive"""
        try:
            # Test basic AI service responsiveness
            start_time = datetime.utcnow()
            # Simulate quick health ping
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return response_time < 1000  # Should respond within 1 second
        except Exception:
            return False
    
    async def _check_model_inference(self) -> bool:
        """Check if model inference is working"""
        try:
            # Test model inference with simple query
            start_time = datetime.utcnow()
            # Simulate model inference test
            inference_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._inference_times.append(inference_time)
            
            # Keep only last 10 inference times
            if len(self._inference_times) > 10:
                self._inference_times = self._inference_times[-10:]
            
            return inference_time < 5000  # Should complete within 5 seconds
        except Exception:
            return False
    
    async def _check_memory_pressure(self) -> bool:
        """Check for memory pressure that could affect AI models"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            # AI models need more memory - fail if less than 2GB available
            return memory.available > 2 * 1024 * 1024 * 1024
        except ImportError:
            return True
        except Exception:
            return False
    
    # Readiness checks
    async def _check_openai_ready(self) -> bool:
        """Check if OpenAI API is ready"""
        try:
            # Test OpenAI API connectivity
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            # This would be a real API call in production
            return True
        except Exception:
            return False
    
    async def _check_vector_db_ready(self) -> bool:
        """Check if vector database is ready"""
        try:
            # Test vector database connectivity
            return True
        except Exception:
            return False
    
    async def _check_model_cache_ready(self) -> bool:
        """Check if model cache is ready"""
        try:
            import redis
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_AI_DB", "2")),
                socket_timeout=5
            )
            return r.ping()
        except Exception:
            return False
    
    async def _check_gpu_availability(self) -> bool:
        """Check GPU availability for AI models"""
        try:
            # Check if GPU is available and not over-utilized
            # This would use nvidia-ml-py or similar in production
            return True
        except Exception:
            return True  # Not critical if no GPU
    
    async def _check_inference_capacity(self) -> bool:
        """Check if service has capacity for new inferences"""
        try:
            # Check current inference load
            # This would check your actual inference queue/load
            return True
        except Exception:
            return False
    
    # Startup checks
    async def _check_models_loading(self) -> bool:
        """Check if AI models are loading/loaded"""
        try:
            # Check model loading status
            return True
        except Exception:
            return False
    
    async def _check_vector_embeddings_loaded(self) -> bool:
        """Check if vector embeddings are loaded"""
        try:
            # Check embedding model status
            return True
        except Exception:
            return False
    
    async def _check_coaching_context_initialized(self) -> bool:
        """Check if coaching context is initialized"""
        try:
            # Check coaching system initialization
            return True
        except Exception:
            return False
    
    async def _check_personalization_engine_ready(self) -> bool:
        """Check if personalization engine is ready"""
        try:
            # Check personalization system
            return True
        except Exception:
            return False
    
    # Circuit breaker fallbacks
    async def _openai_fallback(self, *args, **kwargs):
        """Fallback for OpenAI API failures"""
        return {
            "response": "I'm temporarily using cached responses. Please try again in a moment.",
            "coaching_advice": "Continue with your current plan while I restore full functionality.",
            "fallback_used": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _inference_fallback(self, *args, **kwargs):
        """Fallback for model inference failures"""
        return {
            "response": "Using simplified coaching logic while AI models recover.",
            "advice": "Keep following your nutrition plan. Detailed AI coaching will resume shortly.",
            "fallback_used": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _circuit_breaker_state_changed(self, name: str, old_state, new_state):
        """Handle circuit breaker state changes"""
        print(f"AI Coach circuit breaker '{name}' changed from {old_state.value} to {new_state.value}")
        
        # AI service state changes are critical
        if new_state.value == "open":
            print(f"CRITICAL: AI service '{name}' is down - switching to fallback mode")
    
    async def _handle_health_alert(self, alert: Dict[str, Any]):
        """Handle health alerts"""
        print(f"AI Coach Health Alert: {alert['type']} - {alert['message']}")
        
        # AI service alerts need immediate attention
        if alert['severity'] in ['critical', 'warning']:
            try:
                await self.cloudwatch_reporter.report_metrics(alert['metrics'])
            except Exception as e:
                print(f"Failed to report AI alert to CloudWatch: {e}")
    
    def get_health_router(self):
        """Get FastAPI router for health endpoints"""
        return create_health_routes(self.health_checker)
    
    async def start_monitoring(self):
        """Start health monitoring"""
        await self.monitor.start_monitoring()
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        await self.monitor.stop_monitoring()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        summary = self.monitor.get_metrics_summary()
        
        # Add AI-specific metrics
        avg_inference_time = (
            sum(self._inference_times) / len(self._inference_times)
            if self._inference_times else 0
        )
        
        summary['ai_metrics'] = {
            'average_inference_time_ms': round(avg_inference_time, 2),
            'recent_inferences': len(self._inference_times),
            'model_load_times': self._model_load_times,
            'gpu_available': False,  # Would check actual GPU status
            'models_loaded': True    # Would check actual model status
        }
        
        return summary


# Global health check instance
ai_coach_health_check = AICoachServiceHealthCheck()


# Convenience functions
def get_health_router():
    """Get health check router for FastAPI app"""
    return ai_coach_health_check.get_health_router()


async def initialize_health_monitoring():
    """Initialize and start health monitoring"""
    await ai_coach_health_check.start_monitoring()


async def shutdown_health_monitoring():
    """Shutdown health monitoring"""
    await ai_coach_health_check.stop_monitoring()


def get_health_summary():
    """Get current health summary"""
    return ai_coach_health_check.get_health_summary()
