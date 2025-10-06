"""
Simple AI Configuration Tests
Tests that can run without AWS dependencies
"""

import pytest
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.ai_config import AIConfigManager, AIModel


class TestAIConfiguration:
    """Test AI configuration without AWS dependencies"""
    
    def test_model_selection_free_tier(self):
        """Test model selection for free tier users"""
        ai_config = AIConfigManager()
        
        model = ai_config.select_optimal_model(
            use_case="quick_answers",
            user_tier="free",
            complexity_score=3.0
        )
        
        # Free tier should get cost-effective models
        assert model.cost_per_1k_tokens <= 0.001
        assert model.model_id is not None
        assert len(model.use_cases) > 0
    
    def test_model_selection_premium_tier(self):
        """Test model selection for premium tier users"""
        ai_config = AIConfigManager()
        
        model = ai_config.select_optimal_model(
            use_case="meal_planning",
            user_tier="premium",
            complexity_score=8.0
        )
        
        # Premium tier should get high quality models
        assert model.quality_score >= 8.0
        assert model.model_id is not None
    
    def test_cost_estimation(self):
        """Test cost estimation functionality"""
        ai_config = AIConfigManager()
        
        model_config = ai_config.model_configs[AIModel.CLAUDE_3_HAIKU]
        cost = ai_config.estimate_cost(
            model_config, 
            prompt_length=1000, 
            expected_response_length=500
        )
        
        assert cost > 0
        assert cost < 0.01  # Should be reasonable
    
    def test_fallback_chain(self):
        """Test fallback chain configuration"""
        ai_config = AIConfigManager()
        
        fallbacks = ai_config.get_fallback_chain(AIModel.CLAUDE_3_OPUS)
        assert len(fallbacks) > 0
        assert AIModel.CLAUDE_3_SONNET in fallbacks
    
    def test_optimized_parameters(self):
        """Test parameter optimization for different request types"""
        ai_config = AIConfigManager()
        
        model_config = ai_config.model_configs[AIModel.CLAUDE_3_HAIKU]
        
        factual_params = ai_config.get_optimized_parameters(model_config, "factual_query")
        creative_params = ai_config.get_optimized_parameters(model_config, "creative_recipe")
        
        # Factual queries should have lower temperature
        assert factual_params["temperature"] < creative_params["temperature"]
        
        # All parameters should be present
        assert "max_tokens" in factual_params
        assert "temperature" in factual_params
        assert "top_p" in factual_params
    
    def test_all_models_configured(self):
        """Test that all models have valid configurations"""
        ai_config = AIConfigManager()
        
        for model_enum in AIModel:
            assert model_enum in ai_config.model_configs
            config = ai_config.model_configs[model_enum]
            
            # Validate configuration
            assert config.model_id
            assert config.cost_per_1k_tokens > 0
            assert 1 <= config.quality_score <= 10
            assert config.max_tokens > 0
            assert len(config.use_cases) > 0
    
    def test_complexity_scoring(self):
        """Test that complexity affects model selection appropriately"""
        ai_config = AIConfigManager()
        
        # Low complexity should prefer cost-effective models
        simple_model = ai_config.select_optimal_model(
            "quick_answers", "standard", complexity_score=2.0
        )
        
        # High complexity should prefer quality models
        complex_model = ai_config.select_optimal_model(
            "detailed_analysis", "standard", complexity_score=9.0
        )
        
        # Quality should generally increase with complexity
        assert complex_model.quality_score >= simple_model.quality_score
    
    def test_user_tier_constraints(self):
        """Test that user tiers are properly enforced"""
        ai_config = AIConfigManager()
        
        # Free tier users should be limited to cheap models
        free_models = []
        for _ in range(10):  # Test multiple scenarios
            model = ai_config.select_optimal_model(
                "nutrition_facts", "free", complexity_score=5.0
            )
            free_models.append(model)
        
        # All should be cost-effective
        for model in free_models:
            assert model.cost_per_1k_tokens <= 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
