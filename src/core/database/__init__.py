"""
Database layer abstractions and optimizations for AI Nutritionist.

This module provides optimized database operations with:
- Repository pattern for data access
- Unit of Work pattern for transaction management
- Query optimization and caching
- Connection pooling
- Performance monitoring
"""

from .abstractions import (
    Repository,
    UnitOfWork,
    QueryBuilder,
    Specification,
    DatabaseError,
    ConnectionPoolError,
    QueryPerformanceError,
)
from .connection_pool import ConnectionPool, DatabaseConfig
from .monitoring import QueryMonitor, PerformanceMetrics
from .cache import QueryCache, CacheStrategy, CacheConfig, get_query_cache
from .optimizations import (
    BatchLoader,
    QueryOptimizer,
    IndexManager,
    SlowQueryDetector,
    IndexRecommendation,
)
from .repositories import (
    UserProfileRepository,
    MealPlanRepository,
    UserByPhoneSpecification,
    ActiveUsersSpecification,
    RecentMealPlansSpecification,
)
from .unit_of_work import DynamoDBUnitOfWork, ChangeTracker
from .dashboard import DatabaseDashboard, AlertManager, get_database_dashboard

__all__ = [
    # Core abstractions
    "Repository",
    "UnitOfWork", 
    "QueryBuilder",
    "Specification",
    "Entity",
    # Errors
    "DatabaseError",
    "ConnectionPoolError",
    "QueryPerformanceError",
    # Metrics
    "QueryMetrics",
    "PerformanceMetrics",
    # Connection management
    "ConnectionPool",
    "DatabaseConfig",
    "get_connection_pool",
    # Monitoring
    "QueryMonitor",
    "get_query_monitor",
    # Caching
    "QueryCache",
    "CacheStrategy",
    "CacheConfig",
    "get_query_cache",
    # Optimizations
    "BatchLoader",
    "QueryOptimizer",
    "IndexManager", 
    "SlowQueryDetector",
    "IndexRecommendation",
    # Repositories
    "UserProfileRepository",
    "MealPlanRepository",
    "UserByPhoneSpecification",
    "ActiveUsersSpecification",
    "RecentMealPlansSpecification",
    # Unit of Work
    "DynamoDBUnitOfWork",
    "ChangeTracker",
    # Dashboard and alerts
    "DatabaseDashboard",
    "AlertManager",
    "get_database_dashboard",
]

from .abstractions import (
    Repository,
    UnitOfWork,
    QueryBuilder,
    Specification,
    DatabaseError,
    ConnectionPoolError,
    QueryPerformanceError,
)
from .cache import QueryCache, CacheStrategy
from .connection_pool import ConnectionPool, DatabaseConfig
from .monitoring import QueryMonitor, PerformanceMetrics
from .optimizations import (
    BatchLoader,
    EagerLoader,
    QueryOptimizer,
    IndexManager,
    SlowQueryDetector,
)
from .specifications import (
    BaseSpecification,
    AndSpecification,
    OrSpecification,
    NotSpecification,
)
from .uow import SqlUnitOfWork
from .repositories import (
    AsyncSqlRepository,
    SqlUserRepository,
    SqlMealPlanRepository,
    SqlUsageAnalyticsRepository,
)

__all__ = [
    # Core abstractions
    "Repository",
    "UnitOfWork",
    "QueryBuilder",
    "Specification",
    # Specification helpers
    "BaseSpecification",
    "AndSpecification",
    "OrSpecification",
    "NotSpecification",
    # Errors
    "DatabaseError",
    "ConnectionPoolError",
    "QueryPerformanceError",
    # Connection management
    "ConnectionPool",
    "DatabaseConfig",
    "SqlUnitOfWork",
    # Monitoring
    "QueryMonitor",
    "PerformanceMetrics",
    # Caching
    "QueryCache",
    "CacheStrategy",
    # Optimizations
    "BatchLoader",
    "EagerLoader",
    "QueryOptimizer",
    "IndexManager",
    "SlowQueryDetector",
    # Repositories
    "AsyncSqlRepository",
    "SqlUserRepository",
    "SqlMealPlanRepository",
    "SqlUsageAnalyticsRepository",
]
