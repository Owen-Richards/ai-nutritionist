"""API layer for service.

REST API controllers, schemas, and routing.
"""

from .controllers import (
    MealPlanController,
    UserController,
    SubscriptionController
)
from .schemas import (
    MealPlanSchema,
    UserSchema,
    SubscriptionSchema
)
from .middleware import (
    AuthenticationMiddleware,
    ValidationMiddleware,
    ErrorHandlingMiddleware
)
from .routing import router

__all__ = [
    # Controllers
    "MealPlanController",
    "UserController",
    "SubscriptionController",
    
    # Schemas
    "MealPlanSchema",
    "UserSchema", 
    "SubscriptionSchema",
    
    # Middleware
    "AuthenticationMiddleware",
    "ValidationMiddleware",
    "ErrorHandlingMiddleware",
    
    # Routing
    "router",
]
