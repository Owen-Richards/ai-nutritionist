"""
AI_CONTEXT
Purpose: Infrastructure services providing cross-cutting concerns for resilience, monitoring, and compliance
Public API: AIService, CachingService, ErrorRecoveryService, MonitoringService, observability utilities, 
            rate_limiter, secrets_manager, privacy_service, incident_manager
Internal: Implementation details in submodules
Contracts: All services follow dependency injection pattern, async for I/O operations
Side Effects: AWS API calls (Bedrock, CloudWatch, Secrets Manager), metrics emission, log generation
Stability: public - maintain backward compatibility for all exported services
Usage Example:
    from services.infrastructure import observability, rate_limiter
    
    @trace_operation("api_call")
    @check_rate_limit(max_requests=10, window_seconds=60)
    async def protected_endpoint(request):
        logger = observability.get_logger(__name__)
        logger.info("Processing request", extra={"request_id": request.id})
        return response
"""

"""
Infrastructure Services - Technical foundation supporting the entire application

Core Services:
- AI/ML capabilities and model integration (AWS Bedrock)
- Caching and performance optimization (multi-level caching)
- Error recovery and system resilience (circuit breakers, retries)
- Monitoring and observability (CloudWatch, structured logging)
- User experience enhancement
- System dashboard and analytics

Track G - Reliability, Security, Compliance:
- G1 Observability: structured logs, traces, RED metrics, SLO monitoring
- G2 Rate limiting and abuse protection with per-user/IP controls
- G3 Secrets management with rotation and audit logging
- G4 Privacy compliance with GDPR/CCPA support and DSAR processing
- G5 Incident management with runbooks and disaster recovery
"""

from .ai import AIService
from .caching import AdvancedCachingService
from .resilience import ErrorRecoveryService
from .monitoring import PerformanceMonitoringService
from .experience import EnhancedUserExperienceService
from .dashboard import ImprovementDashboard
from .agent import ReasoningAgent

# Track G services
from .observability import observability, log_info, log_error, trace_operation
from .distributed_rate_limiting import rate_limiter, check_rate_limit
from .secrets_manager import secrets_manager, get_secret, store_secret, secret_context
from .privacy_compliance import privacy_service, record_consent, check_processing_consent, request_data_deletion
from .incident_management import incident_manager, create_incident, get_runbook, escalate_incident

__all__ = [
    'AIService',
    'AdvancedCachingService', 
    'ErrorRecoveryService',
    'PerformanceMonitoringService',
    'EnhancedUserExperienceService',
    'ImprovementDashboard',
    'ReasoningAgent',
    
    # Track G - Observability
    'observability',
    'log_info',
    'log_error', 
    'trace_operation',
    
    # Track G - Rate Limiting  
    'rate_limiter',
    'check_rate_limit',
    'check_rate_limit',
    
    # Track G - Secrets Management
    'secrets_manager',
    'get_secret',
    'store_secret',
    'secret_context',
    
    # Track G - Privacy & Compliance
    'privacy_service',
    'record_consent',
    'check_processing_consent',
    'request_data_deletion',
    
    # Track G - Incident Management
    'incident_manager',
    'create_incident',
    'get_runbook',
    'escalate_incident'
]

# Service factory functions for easy instantiation
def get_ai_service():
    """Get AI service instance"""
    return AIService()

def get_caching_service():
    """Get advanced caching service instance"""
    return AdvancedCachingService()

def get_resilience_service():
    """Get error recovery service instance"""
    return ErrorRecoveryService()

def get_monitoring_service():
    """Get performance monitoring service instance"""
    return PerformanceMonitoringService()

def get_experience_service():
    """Get enhanced user experience service instance"""
    return EnhancedUserExperienceService()

def get_dashboard_service():
    """Get improvement dashboard service instance"""
    return ImprovementDashboard()

def get_observability_service():
    """Get observability service instance"""
    return observability

def get_rate_limiter():
    """Get rate limiter service instance"""
    return rate_limiter

def get_secrets_manager():
    """Get secrets manager service instance"""
    return secrets_manager

def get_privacy_service():
    """Get privacy compliance service instance"""
    return privacy_service

def get_incident_manager():
    """Get incident manager service instance"""
    return incident_manager
