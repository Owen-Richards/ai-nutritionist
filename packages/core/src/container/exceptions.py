"""
DI Container Exceptions
======================

Custom exceptions for dependency injection system.
"""

from typing import List, Type


class DIException(Exception):
    """Base exception for DI container errors."""
    pass


class ServiceNotRegisteredException(DIException):
    """Raised when attempting to resolve an unregistered service."""
    
    def __init__(self, service_type: Type):
        self.service_type = service_type
        super().__init__(f"Service {service_type.__name__} is not registered in the container")


class CircularDependencyException(DIException):
    """Raised when a circular dependency is detected."""
    
    def __init__(self, dependency_chain: List[Type]):
        self.dependency_chain = dependency_chain
        chain_names = " -> ".join(t.__name__ for t in dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_names}")


class InvalidLifetimeException(DIException):
    """Raised when an invalid service lifetime is specified."""
    
    def __init__(self, lifetime: str):
        self.lifetime = lifetime
        super().__init__(f"Invalid service lifetime: {lifetime}")


class FactoryException(DIException):
    """Raised when a factory function fails."""
    
    def __init__(self, factory_name: str, error: Exception):
        self.factory_name = factory_name
        self.error = error
        super().__init__(f"Factory '{factory_name}' failed: {error}")


class ConfigurationException(DIException):
    """Raised when configuration injection fails."""
    
    def __init__(self, config_key: str, error: str = None):
        self.config_key = config_key
        self.error = error
        message = f"Configuration key '{config_key}' not found"
        if error:
            message += f": {error}"
        super().__init__(message)


class ScopeException(DIException):
    """Raised when scope operations fail."""
    
    def __init__(self, message: str):
        super().__init__(f"Scope error: {message}")
