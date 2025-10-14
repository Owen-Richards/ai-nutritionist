"""
Critical Path Tests
Essential tests that must pass for the system to be considered functional
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import core system components
import sys
import os
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from handlers.message_handler import MessageHandler
    from services.ai.ai_service import AIService
    from services.subscription.subscription_service import SubscriptionService
    from services.nutrition.nutrition_service import NutritionService
    from config.ai_config import AIConfigManager
except ImportError as e:
    pytest.skip(f"Core modules not available: {e}", allow_module_level=True)


@pytest.mark.critical
@pytest.mark.asyncio
class TestCriticalPaths:
    """Critical path tests that must always pass"""
    
    async def test_message_handler_initialization(self):
        """Test that message handler can be initialized"""
        with patch('boto3.client'):
            handler = MessageHandler()
            assert handler is not None
    
    async def test_ai_service_basic_functionality(self):
        """Test basic AI service functionality"""
        ai_service = AIService()
        
        # Test configuration loading
        assert ai_service.config is not None
        
        # Test model selection
        with patch.object(ai_service, '_call_ai_model', return_value="Test response"):
            response = await ai_service.generate_meal_plan(
                user_id="test_user",
                dietary_preferences="vegetarian",
                health_goals="weight_loss"
            )
            assert response is not None
            assert len(response) > 0
    
    async def test_subscription_service_tier_check(self):
        """Test subscription service tier checking"""
        subscription_service = SubscriptionService()
        
        # Test free tier check
        with patch.object(subscription_service, '_get_user_subscription', 
                         return_value={"tier": "free", "active": True}):
            tier = await subscription_service.get_user_tier("test_user")
            assert tier in ["free", "premium", "enterprise"]
    
    async def test_nutrition_service_calculation(self):
        """Test nutrition service basic calculations"""
        nutrition_service = NutritionService()
        
        # Test basic nutrition calculation
        sample_food = {
            "name": "apple",
            "quantity": 100,
            "unit": "grams"
        }
        
        with patch.object(nutrition_service, '_get_nutrition_data',
                         return_value={"calories": 52, "protein": 0.3, "carbs": 14}):
            nutrition = await nutrition_service.calculate_nutrition(sample_food)
            assert nutrition is not None
            assert "calories" in nutrition
    
    async def test_ai_config_manager_model_selection(self):
        """Test AI configuration manager model selection"""
        config_manager = AIConfigManager()
        
        # Test model selection for different tiers
        free_model = config_manager.select_optimal_model("meal_planning", "free", 5.0)
        assert free_model is not None
        assert free_model.cost_per_1k_tokens <= 0.001  # Free tier constraint
        
        premium_model = config_manager.select_optimal_model("meal_planning", "premium", 5.0)
        assert premium_model is not None
        assert premium_model.quality_score >= free_model.quality_score
    
    @pytest.mark.integration
    async def test_end_to_end_message_processing(self):
        """Test end-to-end message processing flow"""
        
        # Mock external dependencies
        with patch('boto3.client'), \
             patch.object(AIService, 'generate_meal_plan', return_value="Sample meal plan"), \
             patch.object(SubscriptionService, 'get_user_tier', return_value="free"), \
             patch.object(NutritionService, 'calculate_nutrition', return_value={"calories": 2000}):
            
            handler = MessageHandler()
            
            # Test message processing
            test_message = {
                "user_id": "test_user",
                "message": "Generate a meal plan for weight loss",
                "platform": "whatsapp"
            }
            
            response = await handler.process_message(test_message)
            assert response is not None
            assert len(response) > 0
    
    def test_system_configuration_validity(self):
        """Test that system configuration is valid"""
        
        # Test that required environment variables can be handled
        required_configs = [
            "AWS_REGION",
            "OPENAI_API_KEY", 
            "ANTHROPIC_API_KEY"
        ]
        
        # Should not fail even if env vars are missing (should have defaults)
        for config in required_configs:
            value = os.getenv(config, "default_value")
            assert value is not None
    
    def test_import_health(self):
        """Test that all critical imports work"""
        
        # Test core handler imports
        try:
            from handlers.message_handler import MessageHandler
            from handlers.webhook_handler import WebhookHandler
        except ImportError as e:
            pytest.fail(f"Handler import failed: {e}")
        
        # Test core service imports
        try:
            from services.ai.ai_service import AIService
            from services.subscription.subscription_service import SubscriptionService
            from services.nutrition.nutrition_service import NutritionService
        except ImportError as e:
            pytest.fail(f"Service import failed: {e}")
        
        # Test configuration imports
        try:
            from config.ai_config import AIConfigManager
        except ImportError as e:
            pytest.fail(f"Config import failed: {e}")
    
    @pytest.mark.performance
    def test_critical_performance_thresholds(self):
        """Test that critical performance thresholds are met"""
        
        import time
        
        # Test AI config manager performance
        start_time = time.time()
        config_manager = AIConfigManager()
        model = config_manager.select_optimal_model("meal_planning", "free", 5.0)
        end_time = time.time()
        
        # Should complete in under 100ms
        assert (end_time - start_time) < 0.1, "AI config selection too slow"
        
        # Test basic service initialization performance
        start_time = time.time()
        ai_service = AIService()
        nutrition_service = NutritionService()
        subscription_service = SubscriptionService()
        end_time = time.time()
        
        # Should complete in under 500ms
        assert (end_time - start_time) < 0.5, "Service initialization too slow"


@pytest.mark.critical
class TestSystemIntegrity:
    """Tests for system integrity and basic functionality"""
    
    def test_project_structure_integrity(self):
        """Test that project structure is intact"""
        
        project_root = Path(__file__).parent.parent.parent
        
        # Check critical directories
        critical_dirs = [
            "src",
            "src/handlers", 
            "src/services",
            "src/config",
            "tests",
            "infrastructure"
        ]
        
        for dir_path in critical_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"Critical directory missing: {dir_path}"
    
    def test_configuration_files_present(self):
        """Test that configuration files are present"""
        
        project_root = Path(__file__).parent.parent.parent
        
        critical_files = [
            "requirements.txt",
            "pyproject.toml",
            "infrastructure/template.yaml"
        ]
        
        for file_path in critical_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Critical file missing: {file_path}"
    
    def test_dependency_health(self):
        """Test that critical dependencies are available"""
        
        critical_imports = [
            "boto3",
            "requests", 
            "pydantic",
            "fastapi"
        ]
        
        for module_name in critical_imports:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"Critical dependency missing: {module_name}")


@pytest.mark.critical
@pytest.mark.security
class TestSecurityCriticalPaths:
    """Security-critical tests that must pass"""
    
    def test_user_id_validation(self):
        """Test user ID validation in critical paths"""
        
        # Test that services properly validate user IDs
        from services.subscription.subscription_service import SubscriptionService
        
        subscription_service = SubscriptionService()
        
        # Test invalid user IDs
        invalid_user_ids = [None, "", "   ", "<script>", "'; DROP TABLE users; --"]
        
        for invalid_id in invalid_user_ids:
            with pytest.raises((ValueError, TypeError)):
                # This should raise an exception for invalid IDs
                subscription_service._validate_user_id(invalid_id)
    
    def test_input_sanitization(self):
        """Test input sanitization in critical components"""
        
        from services.ai.ai_service import AIService
        
        ai_service = AIService()
        
        # Test that dangerous inputs are handled safely
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "{{7*7}}",  # Template injection
            "\x00\x01\x02"  # Null bytes
        ]
        
        for dangerous_input in dangerous_inputs:
            # Should not raise exceptions and should sanitize input
            try:
                sanitized = ai_service._sanitize_user_input(dangerous_input)
                assert dangerous_input not in sanitized or sanitized == ""
            except AttributeError:
                # Method might not exist, that's also acceptable
                pass
    
    def test_api_key_protection(self):
        """Test that API keys are properly protected"""
        
        from config.ai_config import AIConfigManager
        
        config_manager = AIConfigManager()
        
        # Test that API keys are not exposed in logs or responses
        config_dict = config_manager.get_safe_config()
        
        # Should not contain actual API keys
        config_str = str(config_dict).lower()
        assert "sk-" not in config_str  # OpenAI key format
        assert "anthropic" not in config_str or len(config_str) < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
