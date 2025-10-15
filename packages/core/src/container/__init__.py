"""
Dependency Injection Container System
====================================

Enterprise-grade DI container with:
- Service registration and resolution
- Lifetime management (singleton, scoped, transient)
- Automatic injection and constructor resolution
- Configuration and secret injection
- Factory patterns and complex object creation
- Circular dependency detection and resolution
"""

from .container import Container, ServiceLifetime
from .decorators import injectable, singleton, scoped, transient
from .providers import ServiceProvider, ConfigurationProvider, SecretProvider
from .registry import ServiceRegistry
from .exceptions import (
    DIException,
    ServiceNotRegisteredException,
    CircularDependencyException,
    InvalidLifetimeException
)

# Global container instance
_container = None

def get_container() -> Container:
    """Get the global DI container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container

def configure_container(container: Container = None) -> Container:
    """Configure and return the DI container."""
    if container is None:
        container = get_container()
    
    # Register default providers
    container.register_provider(ConfigurationProvider())
    container.register_provider(SecretProvider())
    
    return container

__all__ = [
    'Container',
    'ServiceLifetime',
    'injectable',
    'singleton',
    'scoped',
    'transient',
    'ServiceProvider',
    'ConfigurationProvider',
    'SecretProvider',
    'ServiceRegistry',
    'DIException',
    'ServiceNotRegisteredException',
    'CircularDependencyException',
    'InvalidLifetimeException',
    'get_container',
    'configure_container'
]
