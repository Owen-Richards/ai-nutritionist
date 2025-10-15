"""
Monorepo Service Registration
============================

Automatic service discovery and registration for the AI Nutritionist monorepo.
"""

import os
import importlib
import inspect
from typing import Dict, List, Type, Any, Optional
from pathlib import Path

from packages.core.src.container import Container, injectable, singleton, scoped, transient
from packages.core.src.container.configuration import get_application_config
from packages.core.src.container.lifetime import ServiceLifetime


class ServiceDiscovery:
    """Discovers and registers services throughout the monorepo."""
    
    def __init__(self, container: Container, base_path: str = None):
        self.container = container
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.discovered_services: Dict[str, Type] = {}
        self.registration_errors: List[str] = []
    
    def discover_and_register_all(self) -> Container:
        """Discover and register all services in the monorepo."""
        print("🔍 Starting service discovery...")
        
        # Register configuration first
        self._register_configuration()
        
        # Register AWS services
        self._register_aws_services()
        
        # Discover and register services by module
        self._discover_services_in_path("src/services")
        self._discover_services_in_path("src/adapters")
        self._discover_services_in_path("src/handlers")
        self._discover_services_in_path("packages")
        self._discover_services_in_path("services")  # Microservices
        
        # Register discovered services
        self._register_discovered_services()
        
        # Validate registrations
        self._validate_registrations()
        
        print(f"✅ Service discovery completed. Registered {len(self.discovered_services)} services.")
        return self.container
    
    def _register_configuration(self) -> None:
        """Register configuration services."""
        print("📋 Registering configuration services...")
        
        try:
            from packages.core.src.container.configuration import (
                ApplicationConfig, DatabaseConfig, AIConfig, 
                MessagingConfig, CacheConfig, MonitoringConfig, FeatureFlags
            )
            
            app_config = get_application_config()
            
            # Register main configuration
            self.container.register_instance(ApplicationConfig, app_config)
            
            # Register individual config sections
            self.container.register_instance(DatabaseConfig, app_config.database)
            self.container.register_instance(AIConfig, app_config.ai)
            self.container.register_instance(MessagingConfig, app_config.messaging)
            self.container.register_instance(CacheConfig, app_config.cache)
            self.container.register_instance(MonitoringConfig, app_config.monitoring)
            self.container.register_instance(FeatureFlags, app_config.features)
            
            # Register config dictionaries for legacy services
            self.container.register_factory(
                'database_config',
                lambda: {
                    'table_name': app_config.database.table_name,
                    'region': app_config.database.region,
                    'endpoint_url': app_config.database.endpoint_url
                },
                ServiceLifetime.SINGLETON
            )
            
            self.container.register_factory(
                'ai_config',
                lambda: {
                    'model_name': app_config.ai.model_name,
                    'region': app_config.ai.region,
                    'max_tokens': app_config.ai.max_tokens,
                    'temperature': app_config.ai.temperature
                },
                ServiceLifetime.SINGLETON
            )
            
            self.container.register_factory(
                'cache_config',
                lambda: {
                    'redis_url': app_config.cache.redis_url,
                    'default_ttl': app_config.cache.default_ttl,
                    'max_memory': app_config.cache.max_memory
                },
                ServiceLifetime.SINGLETON
            )
            
            self.container.register_factory(
                'monitoring_config',
                lambda: {
                    'metrics_enabled': app_config.monitoring.metrics_enabled,
                    'tracing_enabled': app_config.monitoring.tracing_enabled,
                    'log_level': app_config.monitoring.log_level
                },
                ServiceLifetime.SINGLETON
            )
            
            print("✅ Configuration services registered")
            
        except Exception as e:
            error = f"Failed to register configuration: {e}"
            print(f"❌ {error}")
            self.registration_errors.append(error)
    
    def _register_aws_services(self) -> None:
        """Register AWS service clients and resources."""
        print("☁️ Registering AWS services...")
        
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, PartialCredentialsError
            
            # Register AWS Session
            self.container.register_factory(
                boto3.Session,
                lambda: boto3.Session(),
                ServiceLifetime.SINGLETON
            )
            
            # Register DynamoDB Resource
            def create_dynamodb_resource():
                try:
                    session = boto3.Session()
                    config = get_application_config()
                    kwargs = {'region_name': config.database.region}
                    if config.database.endpoint_url:
                        kwargs['endpoint_url'] = config.database.endpoint_url
                    return session.resource('dynamodb', **kwargs)
                except (NoCredentialsError, PartialCredentialsError):
                    print("⚠️ AWS credentials not found, using mock DynamoDB")
                    return MockDynamoDBResource()
            
            self.container.register_factory(
                'dynamodb_resource',
                create_dynamodb_resource,
                ServiceLifetime.SINGLETON
            )
            
            # Register other AWS clients
            def create_sns_client():
                try:
                    session = boto3.Session()
                    config = get_application_config()
                    return session.client('sns', region_name=config.messaging.aws_region)
                except (NoCredentialsError, PartialCredentialsError):
                    return MockSNSClient()
            
            def create_bedrock_client():
                try:
                    session = boto3.Session()
                    config = get_application_config()
                    return session.client('bedrock-runtime', region_name=config.ai.region)
                except (NoCredentialsError, PartialCredentialsError):
                    return MockBedrockClient()
            
            self.container.register_factory('sns_client', create_sns_client, ServiceLifetime.SINGLETON)
            self.container.register_factory('bedrock_client', create_bedrock_client, ServiceLifetime.SINGLETON)
            self.container.register_factory('ai_client', create_bedrock_client, ServiceLifetime.SINGLETON)
            
            print("✅ AWS services registered")
            
        except ImportError as e:
            error = f"Failed to register AWS services (boto3 not available): {e}"
            print(f"⚠️ {error}")
            self.registration_errors.append(error)
        except Exception as e:
            error = f"Failed to register AWS services: {e}"
            print(f"❌ {error}")
            self.registration_errors.append(error)
    
    def _discover_services_in_path(self, relative_path: str) -> None:
        """Discover services in a specific path."""
        full_path = self.base_path / relative_path
        if not full_path.exists():
            print(f"⏭️ Skipping {relative_path} (path does not exist)")
            return
        
        print(f"🔍 Discovering services in {relative_path}...")
        
        try:
            # Find all Python files
            python_files = list(full_path.rglob("*.py"))
            
            for py_file in python_files:
                if py_file.name.startswith('__') or py_file.name.startswith('test_'):
                    continue
                
                try:
                    # Convert file path to module path
                    module_path = self._file_to_module_path(py_file)
                    if not module_path:
                        continue
                    
                    # Import module and discover services
                    module = importlib.import_module(module_path)
                    self._discover_services_in_module(module, py_file)
                    
                except Exception as e:
                    # Don't fail discovery due to individual module issues
                    print(f"⚠️ Could not process {py_file}: {e}")
                    continue
        
        except Exception as e:
            error = f"Failed to discover services in {relative_path}: {e}"
            print(f"❌ {error}")
            self.registration_errors.append(error)
    
    def _file_to_module_path(self, file_path: Path) -> Optional[str]:
        """Convert file path to importable module path."""
        try:
            # Get relative path from base
            rel_path = file_path.relative_to(self.base_path)
            
            # Remove .py extension
            module_parts = rel_path.with_suffix('').parts
            
            # Skip certain directories
            if any(part.startswith('.') or part == '__pycache__' for part in module_parts):
                return None
            
            return '.'.join(module_parts)
        
        except ValueError:
            return None
    
    def _discover_services_in_module(self, module, file_path: Path) -> None:
        """Discover services in a specific module."""
        for name, obj in inspect.getmembers(module):
            if self._is_service_class(obj, module):
                service_key = f"{module.__name__}.{name}"
                self.discovered_services[service_key] = obj
                print(f"  📦 Found service: {name}")
    
    def _is_service_class(self, obj, module) -> bool:
        """Check if an object is a service class that should be registered."""
        if not inspect.isclass(obj):
            return False
        
        # Must be defined in this module (not imported)
        if getattr(obj, '__module__', None) != module.__name__:
            return False
        
        # Check for DI decorators
        if hasattr(obj, '_di_injectable'):
            return True
        
        # Check for service naming patterns
        service_patterns = [
            'Service', 'Repository', 'Handler', 'Controller', 
            'Manager', 'Client', 'Adapter', 'Gateway', 'Provider'
        ]
        
        if any(obj.__name__.endswith(pattern) for pattern in service_patterns):
            return True
        
        # Check for abstract base classes that should be interfaces
        if inspect.isabstract(obj):
            return True
        
        return False
    
    def _register_discovered_services(self) -> None:
        """Register all discovered services."""
        print("📋 Registering discovered services...")
        
        for service_key, service_class in self.discovered_services.items():
            try:
                lifetime = self._determine_service_lifetime(service_class)
                
                # Check if it's an interface (abstract class)
                if inspect.isabstract(service_class):
                    # Find concrete implementation
                    implementation = self._find_implementation(service_class)
                    if implementation:
                        self.container.register(service_class, implementation, lifetime)
                        print(f"  🔗 Registered interface: {service_class.__name__} -> {implementation.__name__}")
                    else:
                        print(f"  ⚠️ No implementation found for interface: {service_class.__name__}")
                else:
                    # Register concrete class
                    self.container.register(service_class, lifetime=lifetime)
                    print(f"  ✅ Registered service: {service_class.__name__} ({lifetime.value})")
            
            except Exception as e:
                error = f"Failed to register {service_class.__name__}: {e}"
                print(f"  ❌ {error}")
                self.registration_errors.append(error)
    
    def _determine_service_lifetime(self, service_class: Type) -> ServiceLifetime:
        """Determine the appropriate lifetime for a service."""
        # Check for explicit decorator
        if hasattr(service_class, '_di_lifetime'):
            return service_class._di_lifetime
        
        # Default lifetimes based on patterns
        singleton_patterns = [
            'Cache', 'Config', 'Client', 'Factory', 'Manager', 
            'Provider', 'Gateway', 'Monitor', 'Logger'
        ]
        
        scoped_patterns = [
            'Service', 'Handler', 'Controller', 'Coordinator',
            'Processor', 'Engine', 'Pipeline'
        ]
        
        transient_patterns = [
            'Repository', 'Adapter', 'Builder', 'Validator'
        ]
        
        class_name = service_class.__name__
        
        if any(pattern in class_name for pattern in singleton_patterns):
            return ServiceLifetime.SINGLETON
        elif any(pattern in class_name for pattern in scoped_patterns):
            return ServiceLifetime.SCOPED
        elif any(pattern in class_name for pattern in transient_patterns):
            return ServiceLifetime.TRANSIENT
        
        # Default to scoped for services
        return ServiceLifetime.SCOPED
    
    def _find_implementation(self, interface_class: Type) -> Optional[Type]:
        """Find concrete implementation for an interface."""
        interface_name = interface_class.__name__
        
        # Look for common implementation patterns
        impl_patterns = [
            interface_name.replace('Interface', ''),
            interface_name.replace('Abstract', ''),
            f"{interface_name}Impl",
            f"Default{interface_name}",
            f"Concrete{interface_name}"
        ]
        
        for service_key, service_class in self.discovered_services.items():
            if inspect.isabstract(service_class):
                continue
            
            # Check if it's a subclass
            if issubclass(service_class, interface_class):
                return service_class
            
            # Check naming patterns
            if any(service_class.__name__ == pattern for pattern in impl_patterns):
                return service_class
        
        return None
    
    def _validate_registrations(self) -> None:
        """Validate all service registrations."""
        print("🔍 Validating service registrations...")
        
        validation_issues = self.container.validate_services()
        
        if validation_issues:
            print("⚠️ Validation issues found:")
            for issue in validation_issues:
                print(f"  - {issue}")
                self.registration_errors.append(issue)
        else:
            print("✅ All services validated successfully")
        
        # Print summary
        service_info = self.container.get_service_info()
        print(f"\n📊 Registration Summary:")
        print(f"  Total services: {len(service_info)}")
        
        lifetime_counts = {}
        for info in service_info.values():
            lifetime = info['lifetime']
            lifetime_counts[lifetime] = lifetime_counts.get(lifetime, 0) + 1
        
        for lifetime, count in lifetime_counts.items():
            print(f"  {lifetime}: {count}")
        
        if self.registration_errors:
            print(f"\n❌ Registration errors: {len(self.registration_errors)}")
            for error in self.registration_errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.registration_errors) > 5:
                print(f"  ... and {len(self.registration_errors) - 5} more")


# Mock classes for when AWS services are not available
class MockDynamoDBResource:
    """Mock DynamoDB resource for development/testing."""
    
    def Table(self, table_name: str):
        return MockDynamoDBTable(table_name)


class MockDynamoDBTable:
    """Mock DynamoDB table."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    def get_item(self, Key):
        return {'Item': {'id': Key.get('id', 'mock_id'), 'data': 'mock_data'}}
    
    def put_item(self, Item):
        return {'ResponseMetadata': {'HTTPStatusCode': 200}}


class MockSNSClient:
    """Mock SNS client for development/testing."""
    
    def publish(self, **kwargs):
        return {'MessageId': 'mock-message-id', 'ResponseMetadata': {'HTTPStatusCode': 200}}


class MockBedrockClient:
    """Mock Bedrock client for development/testing."""
    
    def invoke_model(self, **kwargs):
        return {
            'body': type('MockBody', (), {
                'read': lambda: b'{"completion": "Mock AI response"}'
            })(),
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }


def create_auto_configured_container(base_path: str = None) -> Container:
    """Create a container with automatic service discovery and registration."""
    container = Container()
    discovery = ServiceDiscovery(container, base_path)
    return discovery.discover_and_register_all()


def main():
    """Main function for testing service discovery."""
    print("🚀 AI Nutritionist - Service Discovery & Registration")
    print("=" * 60)
    
    container = create_auto_configured_container()
    
    print("\n🧪 Testing service resolution...")
    
    # Test basic resolution
    try:
        from packages.core.src.container.configuration import ApplicationConfig
        config = container.resolve(ApplicationConfig)
        print(f"✅ Resolved ApplicationConfig: {config.environment.value}")
    except Exception as e:
        print(f"❌ Failed to resolve ApplicationConfig: {e}")
    
    # Print service information
    print("\n📋 Registered Services:")
    service_info = container.get_service_info()
    for service_name, info in sorted(service_info.items()):
        deps = ', '.join(info['dependencies']) if info['dependencies'] else 'none'
        print(f"  {service_name} ({info['lifetime']}) - deps: {deps}")


if __name__ == "__main__":
    main()
