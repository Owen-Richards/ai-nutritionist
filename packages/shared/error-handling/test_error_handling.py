"""
Basic test to validate the error handling system works correctly
"""

import asyncio
import sys
import os

# Add the project root to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def test_error_imports():
    """Test that all error handling components can be imported"""
    print("🧪 Testing error handling imports...")
    
    try:
        from packages.shared.error_handling import (
            BaseError, DomainError, ValidationError, NotFoundError,
            InfrastructureError, PaymentError, RateLimitError,
            ErrorHandlingMiddleware, error_handler, circuit_breaker,
            retry_with_backoff, ErrorRecoveryManager, ErrorFormatter,
            ErrorMetricsCollector, UserFriendlyMessages
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_error_creation():
    """Test basic error creation and properties"""
    print("\n🧪 Testing error creation...")
    
    try:
        from packages.shared.error_handling import (
            BaseError, ValidationError, DomainError, ErrorSeverity, ErrorCategory
        )
        
        # Test BaseError
        base_error = BaseError(
            message="Test error",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.BUSINESS_LOGIC
        )
        
        assert base_error.message == "Test error"
        assert base_error.severity == ErrorSeverity.MEDIUM
        assert base_error.error_id is not None
        assert base_error.error_code is not None
        print("✅ BaseError creation successful")
        
        # Test ValidationError
        validation_error = ValidationError(
            message="Invalid email",
            field="email",
            invalid_value="not-an-email",
            validation_rules=["required", "email_format"]
        )
        
        assert validation_error.field == "email"
        assert validation_error.invalid_value == "not-an-email"
        assert "required" in validation_error.validation_rules
        print("✅ ValidationError creation successful")
        
        # Test DomainError
        domain_error = DomainError(
            message="Business rule violation",
            business_rule="age_requirement"
        )
        
        assert domain_error.business_rule == "age_requirement"
        print("✅ DomainError creation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creation test failed: {e}")
        return False

def test_error_formatting():
    """Test error formatting functionality"""
    print("\n🧪 Testing error formatting...")
    
    try:
        from packages.shared.error_handling import (
            ValidationError, ErrorFormatter, UserFriendlyMessages
        )
        
        # Create a test error
        error = ValidationError(
            message="Email is required",
            field="email",
            invalid_value="",
            validation_rules=["required"]
        )
        
        # Test formatter
        formatter = ErrorFormatter()
        
        # Test API formatting
        api_response = formatter.format_for_api(error)
        assert api_response['error'] is True
        assert 'error_id' in api_response
        assert 'message' in api_response
        print("✅ API formatting successful")
        
        # Test user-friendly formatting
        user_message = formatter.format_for_user(error)
        assert isinstance(user_message, str)
        assert len(user_message) > 0
        print("✅ User message formatting successful")
        
        # Test user-friendly messages directly
        friendly_message = UserFriendlyMessages.get_message(error)
        assert isinstance(friendly_message, str)
        print("✅ UserFriendlyMessages successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error formatting test failed: {e}")
        return False

def test_decorators():
    """Test error handling decorators"""
    print("\n🧪 Testing decorators...")
    
    try:
        from packages.shared.error_handling import (
            error_handler, ValidationError
        )
        
        # Test error_handler decorator
        @error_handler(log_errors=False, collect_metrics=False, reraise=True)
        def test_function(value):
            if not value:
                raise ValidationError("Value is required", field="value")
            return f"Success: {value}"
        
        # Test successful execution
        result = test_function("test")
        assert result == "Success: test"
        print("✅ Successful function execution")
        
        # Test error handling
        try:
            test_function("")
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert e.field == "value"
            print("✅ Error handling with decorator successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Decorator test failed: {e}")
        return False

async def test_recovery_manager():
    """Test error recovery manager"""
    print("\n🧪 Testing recovery manager...")
    
    try:
        from packages.shared.error_handling import (
            ErrorRecoveryManager, InfrastructureError
        )
        
        recovery_manager = ErrorRecoveryManager()
        
        # Test function that always succeeds
        async def success_function():
            return {"success": True, "data": "test"}
        
        result = await recovery_manager.execute_with_recovery(
            func=success_function,
            operation_name="test_operation"
        )
        
        assert result['success'] is True
        assert result['data']['success'] is True
        print("✅ Successful operation with recovery manager")
        
        # Test function that fails but has fallback
        async def failing_function():
            raise InfrastructureError("Service unavailable", service_name="test")
        
        result = await recovery_manager.execute_with_recovery(
            func=failing_function,
            operation_name="test_failing_operation",
            fallback_type="test"
        )
        
        # Should return fallback response
        assert 'fallback' in result or not result['success']
        print("✅ Failed operation with fallback successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Recovery manager test failed: {e}")
        return False

def test_metrics_collector():
    """Test error metrics collection"""
    print("\n🧪 Testing metrics collector...")
    
    try:
        from packages.shared.error_handling import (
            ErrorMetricsCollector, ValidationError
        )
        
        metrics_collector = ErrorMetricsCollector()
        
        # Create a test error
        error = ValidationError("Test error", field="test")
        
        # Record the error (should not raise exceptions)
        metrics_collector.record_error(
            error=error,
            operation="test_operation",
            service="test_service"
        )
        
        # Get analytics (should not raise exceptions)
        analytics = metrics_collector.get_error_analytics(1)  # 1 hour window
        
        assert isinstance(analytics, dict)
        assert 'total_errors' in analytics
        print("✅ Metrics collection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Metrics collector test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Error Handling System Tests\n")
    
    tests = [
        ("Import Test", test_error_imports),
        ("Error Creation Test", test_basic_error_creation),
        ("Error Formatting Test", test_error_formatting),
        ("Decorators Test", test_decorators),
        ("Recovery Manager Test", test_recovery_manager),
        ("Metrics Collector Test", test_metrics_collector)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED\n")
            else:
                print(f"❌ {test_name} FAILED\n")
                
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}\n")
    
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Error handling system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
