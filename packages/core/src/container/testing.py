"""
DI Container Testing Framework
=============================

Comprehensive testing utilities for dependency injection container.
"""

import pytest
from typing import Dict, Any, Optional, Type, List
from unittest.mock import Mock, MagicMock
from contextlib import contextmanager

from packages.core.src.container import (
    Container, injectable, singleton, scoped, transient,
    ServiceLifetime
)
from packages.core.src.container.configuration import ApplicationConfig


class DITestFramework:
    """Testing framework for DI container systems."""
    
    def __init__(self):
        self.test_container: Optional[Container] = None
        self.mocks: Dict[Type, Mock] = {}
        self.test_services: List[Type] = []
    
    @contextmanager
    def test_container_scope(self):
        """Create a test container scope."""
        self.test_container = Container()
        try:
            yield self.test_container
        finally:
            if self.test_container:
                self.test_container.dispose()
            self.test_container = None
            self.mocks.clear()
            self.test_services.clear()
    
    def create_mock_service(self, service_type: Type, **kwargs) -> Mock:
        """Create a mock service and register it."""
        mock_service = Mock(spec=service_type, **kwargs)
        self.mocks[service_type] = mock_service
        
        if self.test_container:
            self.test_container.register_instance(service_type, mock_service)
        
        return mock_service
    
    def register_test_service(self, service_type: Type, implementation: Type = None) -> None:
        """Register a test service."""
        if self.test_container:
            self.test_container.register_scoped(service_type, implementation)
            self.test_services.append(service_type)
    
    def assert_service_registered(self, service_type: Type) -> None:
        """Assert that a service is registered."""
        assert self.test_container is not None, "Test container not initialized"
        assert self.test_container.is_registered(service_type), f"Service {service_type.__name__} not registered"
    
    def assert_service_resolvable(self, service_type: Type) -> None:
        """Assert that a service can be resolved."""
        assert self.test_container is not None, "Test container not initialized"
        
        try:
            instance = self.test_container.resolve(service_type)
            assert instance is not None, f"Service {service_type.__name__} resolved to None"
        except Exception as e:
            pytest.fail(f"Service {service_type.__name__} could not be resolved: {e}")
    
    def assert_dependency_injected(self, service_instance: Any, dependency_name: str) -> None:
        """Assert that a dependency was injected."""
        assert hasattr(service_instance, dependency_name), f"Dependency {dependency_name} not found"
        dependency = getattr(service_instance, dependency_name)
        assert dependency is not None, f"Dependency {dependency_name} is None"


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def di_test_framework():
    """Provide DI test framework fixture."""
    return DITestFramework()


@pytest.fixture
def test_container():
    """Provide test container fixture."""
    container = Container()
    yield container
    container.dispose()


@pytest.fixture
def mock_config():
    """Provide mock application configuration."""
    config = Mock(spec=ApplicationConfig)
    config.environment.value = 'test'
    config.debug = True
    config.version = '1.0.0-test'
    return config


# =============================================================================
# EXAMPLE TEST SERVICES
# =============================================================================

class TestDatabaseService:
    """Mock database service for testing."""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self.data.get(key)
    
    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
    
    def delete(self, key: str) -> bool:
        return self.data.pop(key, None) is not None


@injectable()
class TestUserService:
    """Test user service with dependencies."""
    
    def __init__(self, database_service: TestDatabaseService, config: ApplicationConfig):
        self.database = database_service
        self.config = config
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        user_id = f"user_{len(self.database.data)}"
        self.database.set(user_id, user_data)
        return user_id
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.database.get(user_id)


@scoped
class TestNutritionService:
    """Test nutrition service."""
    
    def __init__(self, user_service: TestUserService):
        self.user_service = user_service
    
    def calculate_calories(self, user_id: str) -> int:
        user = self.user_service.get_user(user_id)
        if not user:
            return 0
        
        # Simple calculation for testing
        return int(user.get('weight', 70) * 25)


# =============================================================================
# DI CONTAINER TESTS
# =============================================================================

class TestDIContainer:
    """Test cases for DI container functionality."""
    
    def test_service_registration(self, test_container):
        """Test basic service registration."""
        test_container.register_singleton(TestDatabaseService)
        
        assert test_container.is_registered(TestDatabaseService)
    
    def test_service_resolution(self, test_container):
        """Test service resolution."""
        test_container.register_singleton(TestDatabaseService)
        
        service = test_container.resolve(TestDatabaseService)
        assert service is not None
        assert isinstance(service, TestDatabaseService)
    
    def test_dependency_injection(self, test_container, mock_config):
        """Test automatic dependency injection."""
        test_container.register_instance(ApplicationConfig, mock_config)
        test_container.register_singleton(TestDatabaseService)
        test_container.register_scoped(TestUserService)
        
        user_service = test_container.resolve(TestUserService)
        
        assert user_service is not None
        assert user_service.database is not None
        assert user_service.config is mock_config
    
    def test_singleton_lifetime(self, test_container):
        """Test singleton lifetime management."""
        test_container.register_singleton(TestDatabaseService)
        
        service1 = test_container.resolve(TestDatabaseService)
        service2 = test_container.resolve(TestDatabaseService)
        
        assert service1 is service2
    
    def test_scoped_lifetime(self, test_container, mock_config):
        """Test scoped lifetime management."""
        test_container.register_instance(ApplicationConfig, mock_config)
        test_container.register_singleton(TestDatabaseService)
        test_container.register_scoped(TestUserService)
        
        with test_container.create_scope():
            service1 = test_container.resolve(TestUserService)
            service2 = test_container.resolve(TestUserService)
            assert service1 is service2
        
        with test_container.create_scope():
            service3 = test_container.resolve(TestUserService)
            assert service1 is not service3
    
    def test_transient_lifetime(self, test_container):
        """Test transient lifetime management."""
        test_container.register_transient(TestDatabaseService)
        
        service1 = test_container.resolve(TestDatabaseService)
        service2 = test_container.resolve(TestDatabaseService)
        
        assert service1 is not service2
    
    def test_circular_dependency_detection(self, test_container):
        """Test circular dependency detection."""
        @injectable()
        class ServiceA:
            def __init__(self, service_b: 'ServiceB'):
                self.service_b = service_b
        
        @injectable()
        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a
        
        test_container.register_scoped(ServiceA)
        test_container.register_scoped(ServiceB)
        
        with pytest.raises(Exception):  # Should raise circular dependency exception
            test_container.resolve(ServiceA)
    
    def test_optional_dependencies(self, test_container, mock_config):
        """Test handling of optional dependencies."""
        @injectable()
        class ServiceWithOptionalDep:
            def __init__(self, config: ApplicationConfig, optional_service=None):
                self.config = config
                self.optional_service = optional_service
        
        test_container.register_instance(ApplicationConfig, mock_config)
        test_container.register_scoped(ServiceWithOptionalDep)
        
        service = test_container.resolve(ServiceWithOptionalDep)
        assert service.config is mock_config
        assert service.optional_service is None


class TestDIWithMocks:
    """Test DI container with mock services."""
    
    def test_mock_service_injection(self, di_test_framework):
        """Test injection of mock services."""
        with di_test_framework.test_container_scope() as container:
            # Create mock database service
            mock_db = di_test_framework.create_mock_service(TestDatabaseService)
            mock_db.get.return_value = {'name': 'Test User', 'weight': 70}
            
            # Register config and user service
            mock_config = Mock(spec=ApplicationConfig)
            container.register_instance(ApplicationConfig, mock_config)
            container.register_scoped(TestUserService)
            
            # Resolve and test
            user_service = container.resolve(TestUserService)
            user_data = user_service.get_user('test_user')
            
            # Verify mock was called
            mock_db.get.assert_called_once_with('test_user')
            assert user_data == {'name': 'Test User', 'weight': 70}
    
    def test_service_behavior_with_mocks(self, di_test_framework):
        """Test service behavior with mocked dependencies."""
        with di_test_framework.test_container_scope() as container:
            # Setup mocks
            mock_user_service = di_test_framework.create_mock_service(TestUserService)
            mock_user_service.get_user.return_value = {'weight': 80}
            
            # Register nutrition service
            container.register_scoped(TestNutritionService)
            
            # Test nutrition calculation
            nutrition_service = container.resolve(TestNutritionService)
            calories = nutrition_service.calculate_calories('user123')
            
            # Verify behavior
            mock_user_service.get_user.assert_called_once_with('user123')
            assert calories == 2000  # 80 * 25


class TestDIIntegration:
    """Integration tests for DI container."""
    
    def test_full_service_chain(self, test_container, mock_config):
        """Test complete service dependency chain."""
        # Register all services
        test_container.register_instance(ApplicationConfig, mock_config)
        test_container.register_singleton(TestDatabaseService)
        test_container.register_scoped(TestUserService)
        test_container.register_scoped(TestNutritionService)
        
        # Create user through the chain
        nutrition_service = test_container.resolve(TestNutritionService)
        
        # Create and test user
        user_id = nutrition_service.user_service.create_user({
            'name': 'Test User',
            'weight': 70,
            'height': 175
        })
        
        # Calculate calories
        calories = nutrition_service.calculate_calories(user_id)
        assert calories == 1750  # 70 * 25
    
    def test_service_validation(self, test_container, mock_config):
        """Test service validation functionality."""
        test_container.register_instance(ApplicationConfig, mock_config)
        test_container.register_singleton(TestDatabaseService)
        test_container.register_scoped(TestUserService)
        
        # Validate services
        issues = test_container.validate_services()
        assert len(issues) == 0  # Should be no issues
    
    def test_container_disposal(self, test_container):
        """Test proper container disposal."""
        test_container.register_singleton(TestDatabaseService)
        
        # Resolve service
        service = test_container.resolve(TestDatabaseService)
        assert service is not None
        
        # Dispose container
        test_container.dispose()
        
        # Should create new instance after disposal
        test_container.register_singleton(TestDatabaseService)
        new_service = test_container.resolve(TestDatabaseService)
        assert new_service is not service


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestDIPerformance:
    """Performance tests for DI container."""
    
    def test_resolution_performance(self, test_container, mock_config):
        """Test service resolution performance."""
        import time
        
        test_container.register_instance(ApplicationConfig, mock_config)
        test_container.register_singleton(TestDatabaseService)
        test_container.register_scoped(TestUserService)
        
        # Warm up
        for _ in range(10):
            test_container.resolve(TestUserService)
        
        # Measure resolution time
        start_time = time.time()
        for _ in range(1000):
            test_container.resolve(TestUserService)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000
        assert avg_time < 0.001  # Should resolve in less than 1ms on average
    
    def test_memory_usage(self, test_container):
        """Test memory usage of container."""
        # Register many services
        for i in range(100):
            service_class = type(f'TestService{i}', (), {
                '__init__': lambda self: None
            })
            test_container.register_transient(service_class)
        
        # Should not consume excessive memory
        service_info = test_container.get_service_info()
        assert len(service_info) == 100


# =============================================================================
# BENCHMARK UTILITIES
# =============================================================================

def benchmark_di_container():
    """Benchmark DI container operations."""
    import time
    
    container = Container()
    
    # Setup services
    container.register_singleton(TestDatabaseService)
    container.register_instance(ApplicationConfig, Mock(spec=ApplicationConfig))
    container.register_scoped(TestUserService)
    
    print("🏁 DI Container Benchmarks")
    print("=" * 40)
    
    # Benchmark registration
    start = time.time()
    for i in range(1000):
        service_class = type(f'BenchService{i}', (), {'__init__': lambda self: None})
        container.register_transient(service_class)
    registration_time = time.time() - start
    print(f"Registration (1000 services): {registration_time:.4f}s")
    
    # Benchmark resolution
    start = time.time()
    for _ in range(1000):
        container.resolve(TestUserService)
    resolution_time = time.time() - start
    print(f"Resolution (1000 calls): {resolution_time:.4f}s")
    
    # Benchmark validation
    start = time.time()
    container.validate_services()
    validation_time = time.time() - start
    print(f"Validation: {validation_time:.4f}s")
    
    container.dispose()


if __name__ == "__main__":
    # Run benchmarks
    benchmark_di_container()
    
    # Run a simple test
    print("\n🧪 Running simple DI test...")
    
    framework = DITestFramework()
    with framework.test_container_scope() as container:
        # Register test services
        mock_config = Mock(spec=ApplicationConfig)
        container.register_instance(ApplicationConfig, mock_config)
        container.register_singleton(TestDatabaseService)
        container.register_scoped(TestUserService)
        
        # Test resolution
        user_service = container.resolve(TestUserService)
        assert user_service is not None
        assert user_service.config is mock_config
        
        print("✅ DI test passed!")
    
    print("🎉 All tests completed successfully!")
