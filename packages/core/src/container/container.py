"""
Main DI Container
================

The core dependency injection container with service resolution and lifecycle management.
"""

import threading
from typing import Any, Type, Dict, List, Optional, Callable, TypeVar, Union
import inspect
from contextlib import contextmanager

from .lifetime import (
    ServiceLifetime, ServiceDescriptor, ServiceScope,
    SingletonLifetimeManager, ScopedLifetimeManager, TransientLifetimeManager
)
from .registry import ServiceRegistry, DependencyInfo
from .providers import ServiceProvider, ConfigurationProvider, SecretProvider, FactoryProvider, ExternalServiceProvider
from .exceptions import (
    ServiceNotRegisteredException, CircularDependencyException,
    InvalidLifetimeException, ScopeException
)

T = TypeVar('T')


class Container:
    """
    Enterprise-grade dependency injection container.
    
    Features:
    - Service registration with multiple lifetime strategies
    - Automatic constructor injection
    - Configuration and secret injection
    - Circular dependency detection
    - Scoped service management
    - Provider pattern for external services
    - Thread-safe operations
    """
    
    def __init__(self):
        self._registry = ServiceRegistry()
        self._providers: List[ServiceProvider] = []
        self._lock = threading.RLock()
        
        # Lifetime managers
        self._singleton_manager = SingletonLifetimeManager()
        self._scoped_manager = ScopedLifetimeManager()
        self._transient_manager = TransientLifetimeManager()
        
        # Resolution tracking for circular dependency detection
        self._resolution_stack: threading.local = threading.local()
        
        # Setup default providers
        self._setup_default_providers()
    
    def _setup_default_providers(self) -> None:
        """Setup default service providers."""
        self.register_provider(ConfigurationProvider())
        self.register_provider(SecretProvider())
        self.register_provider(FactoryProvider())
        self.register_provider(ExternalServiceProvider())
    
    def register_provider(self, provider: ServiceProvider) -> None:
        """Register a service provider."""
        with self._lock:
            self._providers.append(provider)
    
    def register_singleton(self, service_type: Type[T], implementation_type: Type[T] = None) -> 'Container':
        """Register a service as singleton."""
        return self.register(service_type, implementation_type, ServiceLifetime.SINGLETON)
    
    def register_scoped(self, service_type: Type[T], implementation_type: Type[T] = None) -> 'Container':
        """Register a service as scoped."""
        return self.register(service_type, implementation_type, ServiceLifetime.SCOPED)
    
    def register_transient(self, service_type: Type[T], implementation_type: Type[T] = None) -> 'Container':
        """Register a service as transient."""
        return self.register(service_type, implementation_type, ServiceLifetime.TRANSIENT)
    
    def register(
        self, 
        service_type: Type[T], 
        implementation_type: Type[T] = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    ) -> 'Container':
        """Register a service with the container."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=lifetime
        )
        
        with self._lock:
            self._registry.register(descriptor)
        
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'Container':
        """Register a service instance (always singleton)."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        with self._lock:
            self._registry.register(descriptor)
        
        return self
    
    def register_factory(
        self, 
        service_type: Type[T], 
        factory: Callable[[], T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    ) -> 'Container':
        """Register a factory function for a service."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        
        with self._lock:
            self._registry.register(descriptor)
        
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        # Check resolution stack for circular dependencies
        if not hasattr(self._resolution_stack, 'stack'):
            self._resolution_stack.stack = []
        
        if service_type in self._resolution_stack.stack:
            chain = self._resolution_stack.stack + [service_type]
            raise CircularDependencyException(chain)
        
        try:
            self._resolution_stack.stack.append(service_type)
            return self._resolve_internal(service_type)
        finally:
            self._resolution_stack.stack.pop()
    
    def _resolve_internal(self, service_type: Type[T]) -> T:
        """Internal service resolution logic."""
        # Try registered services first
        if self._registry.is_registered(service_type):
            descriptor = self._registry.get_descriptor(service_type)
            return self._create_instance(descriptor)
        
        # Try providers
        for provider in self._providers:
            if provider.can_provide(service_type):
                return provider.provide(service_type, self)
        
        # If not found and it's a concrete class, try to create it
        if inspect.isclass(service_type) and not inspect.isabstract(service_type):
            # Auto-register as transient
            self.register_transient(service_type)
            return self.resolve(service_type)
        
        raise ServiceNotRegisteredException(service_type)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance according to its descriptor."""
        # Return existing instance if provided
        if descriptor.instance is not None:
            return descriptor.instance
        
        # Create factory function
        if descriptor.factory is not None:
            factory = lambda: self._call_factory(descriptor.factory)
        else:
            factory = lambda: self._create_from_type(descriptor.implementation_type)
        
        # Use appropriate lifetime manager
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._singleton_manager.get_instance(descriptor, factory)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._scoped_manager.get_instance(descriptor, factory)
        else:  # TRANSIENT
            return self._transient_manager.get_instance(descriptor, factory)
    
    def _create_from_type(self, implementation_type: Type) -> Any:
        """Create an instance from a type using constructor injection."""
        # Get constructor parameters
        try:
            sig = inspect.signature(implementation_type.__init__)
        except (ValueError, TypeError):
            # No constructor signature available
            return implementation_type()
        
        # Resolve constructor dependencies
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                # No type annotation, use default if available
                if param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                continue
            
            try:
                # Try to resolve the dependency
                dependency = self.resolve(param_type)
                kwargs[param_name] = dependency
            except ServiceNotRegisteredException:
                # Dependency not registered
                if param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                else:
                    # Required dependency not available
                    raise ServiceNotRegisteredException(param_type)
        
        return implementation_type(**kwargs)
    
    def _call_factory(self, factory: Callable) -> Any:
        """Call a factory function with dependency injection."""
        try:
            sig = inspect.signature(factory)
        except (ValueError, TypeError):
            # No signature available, call without parameters
            return factory()
        
        # Resolve factory dependencies
        kwargs = {}
        for param_name, param in sig.parameters.items():
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                continue
            
            if param_type == type(self) or param_name == 'container':
                kwargs[param_name] = self
            else:
                try:
                    dependency = self.resolve(param_type)
                    kwargs[param_name] = dependency
                except ServiceNotRegisteredException:
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
        
        return factory(**kwargs)
    
    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """Try to resolve a service, returning None if not found."""
        try:
            return self.resolve(service_type)
        except (ServiceNotRegisteredException, CircularDependencyException):
            return None
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return self._registry.is_registered(service_type)
    
    @contextmanager
    def create_scope(self):
        """Create a new service scope."""
        scope = self._scoped_manager.create_scope()
        self._scoped_manager.enter_scope(scope)
        try:
            yield scope
        finally:
            self._scoped_manager.exit_scope()
            scope.dispose()
    
    def validate_services(self) -> List[str]:
        """Validate all registered services for dependency issues."""
        return self._registry.validate_all_dependencies()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about all registered services."""
        services = self._registry.get_all_services()
        info = {}
        
        for service_type, descriptor in services.items():
            dependencies = []
            try:
                deps = self._registry.get_dependencies(service_type)
                dependencies = [f"{dep.service_type.__name__}({'optional' if dep.is_optional else 'required'})" 
                              for dep in deps]
            except Exception:
                pass
            
            info[service_type.__name__] = {
                'lifetime': descriptor.lifetime.value,
                'implementation': descriptor.implementation_type.__name__ if descriptor.implementation_type else None,
                'has_factory': descriptor.factory is not None,
                'has_instance': descriptor.instance is not None,
                'dependencies': dependencies
            }
        
        return info
    
    def dispose(self) -> None:
        """Dispose of all managed services."""
        with self._lock:
            self._singleton_manager.dispose()
            self._scoped_manager.dispose()
            self._transient_manager.dispose()
            self._registry.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()
