"""
Service Registry
===============

Central registry for service descriptors and dependency resolution.
"""

from typing import Dict, Type, List, Set, Optional, Any, Callable
import inspect
from dataclasses import dataclass

from .lifetime import ServiceDescriptor, ServiceLifetime
from .exceptions import ServiceNotRegisteredException, CircularDependencyException


@dataclass
class DependencyInfo:
    """Information about a service dependency."""
    parameter_name: str
    service_type: Type
    is_optional: bool = False
    default_value: Any = None


class ServiceRegistry:
    """Registry for service descriptors and dependency metadata."""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._dependency_cache: Dict[Type, List[DependencyInfo]] = {}
        self._resolution_stack: Set[Type] = set()
    
    def register(self, descriptor: ServiceDescriptor) -> None:
        """Register a service descriptor."""
        self._services[descriptor.service_type] = descriptor
        # Clear dependency cache for this type
        if descriptor.service_type in self._dependency_cache:
            del self._dependency_cache[descriptor.service_type]
    
    def get_descriptor(self, service_type: Type) -> ServiceDescriptor:
        """Get service descriptor by type."""
        if service_type not in self._services:
            raise ServiceNotRegisteredException(service_type)
        return self._services[service_type]
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services
    
    def get_all_services(self) -> Dict[Type, ServiceDescriptor]:
        """Get all registered services."""
        return self._services.copy()
    
    def get_dependencies(self, service_type: Type) -> List[DependencyInfo]:
        """Get dependency information for a service type."""
        if service_type in self._dependency_cache:
            return self._dependency_cache[service_type]
        
        # Get the implementation type to analyze
        descriptor = self.get_descriptor(service_type)
        target_type = descriptor.implementation_type
        
        dependencies = []
        
        # Analyze constructor parameters
        try:
            sig = inspect.signature(target_type.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Get parameter type annotation
                param_type = param.annotation
                if param_type == inspect.Parameter.empty:
                    continue
                
                # Check if parameter is optional
                is_optional = param.default != inspect.Parameter.empty
                default_value = param.default if is_optional else None
                
                dependencies.append(DependencyInfo(
                    parameter_name=param_name,
                    service_type=param_type,
                    is_optional=is_optional,
                    default_value=default_value
                ))
        
        except (ValueError, TypeError):
            # Constructor signature analysis failed
            pass
        
        # Cache the result
        self._dependency_cache[service_type] = dependencies
        return dependencies
    
    def check_circular_dependencies(self, service_type: Type, visited: Set[Type] = None) -> None:
        """Check for circular dependencies starting from a service type."""
        if visited is None:
            visited = set()
        
        if service_type in visited:
            # Found circular dependency
            chain = list(visited) + [service_type]
            raise CircularDependencyException(chain)
        
        if not self.is_registered(service_type):
            return  # External dependency, skip
        
        visited.add(service_type)
        
        try:
            dependencies = self.get_dependencies(service_type)
            for dep in dependencies:
                if not dep.is_optional:  # Only check required dependencies
                    self.check_circular_dependencies(dep.service_type, visited.copy())
        except ServiceNotRegisteredException:
            pass  # External dependency, skip
        
        visited.remove(service_type)
    
    def get_dependency_graph(self) -> Dict[Type, List[Type]]:
        """Get the complete dependency graph."""
        graph = {}
        
        for service_type in self._services:
            dependencies = []
            try:
                deps = self.get_dependencies(service_type)
                dependencies = [dep.service_type for dep in deps if not dep.is_optional]
            except Exception:
                pass
            
            graph[service_type] = dependencies
        
        return graph
    
    def validate_all_dependencies(self) -> List[str]:
        """Validate all registered services for dependency issues."""
        issues = []
        
        for service_type in self._services:
            try:
                # Check circular dependencies
                self.check_circular_dependencies(service_type)
                
                # Check if all dependencies are registered
                dependencies = self.get_dependencies(service_type)
                for dep in dependencies:
                    if not dep.is_optional and not self.is_registered(dep.service_type):
                        issues.append(f"Service {service_type.__name__} depends on unregistered service {dep.service_type.__name__}")
            
            except CircularDependencyException as e:
                issues.append(f"Circular dependency: {e}")
            except Exception as e:
                issues.append(f"Error validating {service_type.__name__}: {e}")
        
        return issues
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._dependency_cache.clear()
        self._resolution_stack.clear()
