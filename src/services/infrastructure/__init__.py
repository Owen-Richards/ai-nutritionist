"""
Infrastructure Services Domain

Technical foundation services that support the entire application:
- AI/ML capabilities and model integration
- Caching and performance optimization
- Error recovery and system resilience
- Monitoring and observability
- User experience enhancement
- System dashboard and analytics
"""

from .ai import AIService
from .caching import AdvancedCachingService
from .resilience import ErrorRecoveryService
from .monitoring import PerformanceMonitoringService
from .experience import EnhancedUserExperienceService
from .dashboard import ImprovementDashboard

__all__ = [
    'AIService',
    'AdvancedCachingService', 
    'ErrorRecoveryService',
    'PerformanceMonitoringService',
    'EnhancedUserExperienceService',
    'ImprovementDashboard'
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
