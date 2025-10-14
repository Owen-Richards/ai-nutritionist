"""
Quick DI Container Test
======================

Simple test of the DI container without external dependencies.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from packages.core.src.container.container import Container
    from packages.core.src.container.lifetime import ServiceLifetime
    from packages.core.src.container.decorators import injectable, singleton, scoped
    
    print("✅ Core DI imports successful")
    
    # Test basic container functionality
    @injectable()
    class TestService:
        def __init__(self):
            self.name = "TestService"
        
        def get_info(self):
            return f"Service: {self.name}"
    
    @injectable()
    class DependentService:
        def __init__(self, test_service: TestService):
            self.test_service = test_service
        
        def get_combined_info(self):
            return f"Dependent -> {self.test_service.get_info()}"
    
    print("🧪 Testing DI container...")
    
    # Create container
    container = Container()
    
    # Register services
    container.register_singleton(TestService)
    container.register_scoped(DependentService)
    
    print("📋 Services registered successfully")
    
    # Test resolution
    test_service = container.resolve(TestService)
    print(f"✅ TestService resolved: {test_service.get_info()}")
    
    dependent_service = container.resolve(DependentService)
    print(f"✅ DependentService resolved: {dependent_service.get_combined_info()}")
    
    # Test singleton behavior
    test_service2 = container.resolve(TestService)
    assert test_service is test_service2
    print("✅ Singleton behavior confirmed")
    
    # Test service info
    service_info = container.get_service_info()
    print(f"📊 Container has {len(service_info)} registered services:")
    for name, info in service_info.items():
        print(f"  - {name} ({info['lifetime']})")
    
    # Test validation
    issues = container.validate_services()
    if issues:
        print("⚠️ Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Container validation passed")
    
    print("\n🎉 DI Container test completed successfully!")
    print("📦 Core dependency injection system is working correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Some dependencies may be missing. Install them with:")
    print("pip install boto3 redis")

except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()

print("\n🔧 To install missing dependencies:")
print("  pip install boto3 redis flask pytest")
print("\n🚀 To run full system:")
print("  python packages/core/src/container/startup.py")
