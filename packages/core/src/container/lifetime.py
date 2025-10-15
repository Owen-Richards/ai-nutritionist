"""
Service Lifetime Management
==========================

Defines how services are instantiated and managed.
"""

from enum import Enum
from typing import Any, Dict, Type, Optional, Callable
from abc import ABC, abstractmethod
import threading
import weakref


class ServiceLifetime(Enum):
    """Service lifetime management strategies."""
    SINGLETON = "singleton"     # One instance per container
    SCOPED = "scoped"          # One instance per scope
    TRANSIENT = "transient"    # New instance every time


class ServiceDescriptor:
    """Describes how a service should be registered and resolved."""
    
    def __init__(
        self,
        service_type: Type,
        implementation_type: Type = None,
        factory: Callable = None,
        instance: Any = None,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    ):
        self.service_type = service_type
        self.implementation_type = implementation_type or service_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        
        # Validation
        if sum(x is not None for x in [implementation_type, factory, instance]) != 1:
            raise ValueError("Exactly one of implementation_type, factory, or instance must be provided")


class ServiceInstance:
    """Wrapper for service instances with metadata."""
    
    def __init__(self, instance: Any, lifetime: ServiceLifetime, scope_id: str = None):
        self.instance = instance
        self.lifetime = lifetime
        self.scope_id = scope_id
        self.created_at = threading.current_thread().ident
        self.ref_count = 0


class ServiceScope:
    """Manages scoped service instances."""
    
    def __init__(self, scope_id: str = None):
        self.scope_id = scope_id or f"scope_{id(self)}"
        self._instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._disposed = False
    
    def get_instance(self, service_type: Type) -> Optional[Any]:
        """Get a scoped instance if it exists."""
        with self._lock:
            if self._disposed:
                return None
            return self._instances.get(service_type)
    
    def set_instance(self, service_type: Type, instance: Any) -> None:
        """Store a scoped instance."""
        with self._lock:
            if not self._disposed:
                self._instances[service_type] = instance
    
    def dispose(self) -> None:
        """Dispose of all scoped instances."""
        with self._lock:
            if self._disposed:
                return
            
            # Call dispose on instances that support it
            for instance in self._instances.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception:
                        pass  # Log error in production
            
            self._instances.clear()
            self._disposed = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


class LifetimeManager(ABC):
    """Abstract base for lifetime managers."""
    
    @abstractmethod
    def get_instance(self, descriptor: ServiceDescriptor, factory: Callable) -> Any:
        """Get an instance according to the lifetime strategy."""
        pass
    
    @abstractmethod
    def dispose(self) -> None:
        """Dispose of managed instances."""
        pass


class SingletonLifetimeManager(LifetimeManager):
    """Manages singleton instances."""
    
    def __init__(self):
        self._instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
    
    def get_instance(self, descriptor: ServiceDescriptor, factory: Callable) -> Any:
        """Get or create singleton instance."""
        with self._lock:
            if descriptor.service_type not in self._instances:
                instance = factory()
                self._instances[descriptor.service_type] = instance
            return self._instances[descriptor.service_type]
    
    def dispose(self) -> None:
        """Dispose of all singleton instances."""
        with self._lock:
            for instance in self._instances.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception:
                        pass  # Log error in production
            self._instances.clear()


class ScopedLifetimeManager(LifetimeManager):
    """Manages scoped instances."""
    
    def __init__(self):
        self._scopes: weakref.WeakValueDictionary[str, ServiceScope] = weakref.WeakValueDictionary()
        self._current_scope: threading.local = threading.local()
        self._lock = threading.RLock()
    
    def get_instance(self, descriptor: ServiceDescriptor, factory: Callable) -> Any:
        """Get or create scoped instance."""
        scope = self.get_current_scope()
        if scope is None:
            # No scope, create transient instance
            return factory()
        
        instance = scope.get_instance(descriptor.service_type)
        if instance is None:
            instance = factory()
            scope.set_instance(descriptor.service_type, instance)
        
        return instance
    
    def get_current_scope(self) -> Optional[ServiceScope]:
        """Get the current scope for this thread."""
        return getattr(self._current_scope, 'scope', None)
    
    def create_scope(self) -> ServiceScope:
        """Create a new scope."""
        scope = ServiceScope()
        with self._lock:
            self._scopes[scope.scope_id] = scope
        return scope
    
    def enter_scope(self, scope: ServiceScope) -> None:
        """Enter a scope for the current thread."""
        self._current_scope.scope = scope
    
    def exit_scope(self) -> None:
        """Exit the current scope."""
        if hasattr(self._current_scope, 'scope'):
            delattr(self._current_scope, 'scope')
    
    def dispose(self) -> None:
        """Dispose of all scoped instances."""
        with self._lock:
            for scope in list(self._scopes.values()):
                scope.dispose()
            self._scopes.clear()


class TransientLifetimeManager(LifetimeManager):
    """Manages transient instances (always creates new)."""
    
    def get_instance(self, descriptor: ServiceDescriptor, factory: Callable) -> Any:
        """Always create a new instance."""
        return factory()
    
    def dispose(self) -> None:
        """Nothing to dispose for transient instances."""
        pass
