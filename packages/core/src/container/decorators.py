"""
Dependency Injection Decorators
===============================

Decorators for marking classes and methods for dependency injection.
"""

from typing import Type, Callable, Any, Optional
from functools import wraps

from .lifetime import ServiceLifetime


def injectable(lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
    """Mark a class as injectable with the specified lifetime."""
    def decorator(cls: Type) -> Type:
        cls._di_lifetime = lifetime
        cls._di_injectable = True
        return cls
    return decorator


def singleton(cls: Type) -> Type:
    """Mark a class as a singleton service."""
    return injectable(ServiceLifetime.SINGLETON)(cls)


def scoped(cls: Type) -> Type:
    """Mark a class as a scoped service."""
    return injectable(ServiceLifetime.SCOPED)(cls)


def transient(cls: Type) -> Type:
    """Mark a class as a transient service."""
    return injectable(ServiceLifetime.TRANSIENT)(cls)


def inject(service_type: Type = None, optional: bool = False):
    """Mark a parameter for dependency injection."""
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_di_injections'):
            func._di_injections = {}
        
        # Get parameter name from the original function signature
        import inspect
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        # Find the parameter to inject (last one if not specified)
        if len(param_names) > 0:
            param_name = param_names[-1] if service_type is None else None
            for name, param in sig.parameters.items():
                if param.annotation == service_type:
                    param_name = name
                    break
            
            if param_name:
                func._di_injections[param_name] = {
                    'service_type': service_type or sig.parameters[param_name].annotation,
                    'optional': optional
                }
        
        return func
    return decorator


def factory(service_type: Type):
    """Mark a method as a factory for a service type."""
    def decorator(func: Callable) -> Callable:
        func._di_factory_for = service_type
        return func
    return decorator


def configure(config_section: str = None):
    """Mark a parameter for configuration injection."""
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_di_config_injections'):
            func._di_config_injections = {}
        
        import inspect
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        if len(param_names) > 0:
            param_name = param_names[-1]
            func._di_config_injections[param_name] = config_section or param_name
        
        return func
    return decorator


def secret(secret_key: str = None):
    """Mark a parameter for secret injection."""
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_di_secret_injections'):
            func._di_secret_injections = {}
        
        import inspect
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        if len(param_names) > 0:
            param_name = param_names[-1]
            func._di_secret_injections[param_name] = secret_key or param_name
        
        return func
    return decorator


def autowired(cls: Type) -> Type:
    """Automatically wire dependencies for a class constructor."""
    original_init = cls.__init__
    
    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        # Get DI container and resolve dependencies
        from . import get_container
        container = get_container()
        
        import inspect
        sig = inspect.signature(original_init)
        
        # Resolve dependencies for parameters not provided
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                try:
                    dependency = container.resolve(param.annotation)
                    kwargs[param_name] = dependency
                except Exception:
                    # If dependency resolution fails and parameter has default, use default
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        raise
        
        original_init(self, *args, **kwargs)
    
    cls.__init__ = new_init
    cls._di_autowired = True
    return cls


def lazy_inject(service_type: Type):
    """Create a lazy-loaded dependency property."""
    def decorator(cls: Type) -> Type:
        property_name = f"_{service_type.__name__.lower()}"
        
        def lazy_property(self):
            if not hasattr(self, property_name):
                from . import get_container
                container = get_container()
                setattr(self, property_name, container.resolve(service_type))
            return getattr(self, property_name)
        
        setattr(cls, service_type.__name__.lower(), property(lazy_property))
        return cls
    
    return decorator
