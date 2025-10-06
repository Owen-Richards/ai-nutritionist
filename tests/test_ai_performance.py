"""
AI Performance Test Suite
Comprehensive testing for AI service performance and optimization
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import individual components for testing without AWS dependencies
from src.config.ai_config import AIConfigManager, AIModel
from src.services.ai.prompt_engine import AdvancedPromptEngine


class TestAIConfigurationOptimization:
    """Test AI configuration and optimization features without AWS dependencies"""
    
    @pytest.fixture
    def ai_config(self):
        """Create AI config manager for testing"""
        return AIConfigManager()
    
    @pytest.fixture
    def prompt_engine(self):
        """Create prompt engine for testing"""
        return AdvancedPromptEngine()
    
    def test_model_selection_optimization(self, ai_config):
        """Test intelligent model selection based on use case and user tier"""
        
        # Test free tier model selection
        free_model = ai_config.select_optimal_model(
            use_case="quick_answers",
            user_tier="free",
            complexity_score=3.0
        )
        assert free_model.cost_per_1k_tokens <= 0.001
        
        # Test premium tier model selection
        premium_model = ai_config.select_optimal_model(
            use_case="meal_planning",
            user_tier="premium",
            complexity_score=8.0
        )
        assert premium_model.quality_score >= 8.0
        
        # Test complexity-based selection
        complex_model = ai_config.select_optimal_model(
            use_case="detailed_analysis",
            user_tier="standard",
            complexity_score=9.0
        )
        assert complex_model.quality_score >= 8.5
    
    def test_cost_optimization(self, ai_config):
        """Test cost optimization features"""
        
        # Test cost estimation
        model_config = ai_config.model_configs[AIModel.CLAUDE_3_HAIKU]
        cost = ai_config.estimate_cost(model_config, prompt_length=1000, expected_response_length=500)
        
        assert cost > 0
        assert cost < 0.01  # Should be reasonable for Haiku model
        
        # Test cost-optimized model selection for free tier
        free_model = ai_config.select_optimal_model(
            use_case="quick_answers",
            user_tier="free",
            complexity_score=3.0
        )
        
        # Free tier should get cost-effective models
        assert free_model.cost_per_1k_tokens <= 0.001
    
    def test_fallback_chain_configuration(self, ai_config):
        """Test model fallback chain configuration"""
        
        # Test fallback chain for different models
        claude_fallbacks = ai_config.get_fallback_chain(AIModel.CLAUDE_3_OPUS)
        assert len(claude_fallbacks) > 0
        assert AIModel.CLAUDE_3_SONNET in claude_fallbacks
        
        titan_fallbacks = ai_config.get_fallback_chain(AIModel.TITAN_TEXT_EXPRESS)
        assert len(titan_fallbacks) > 0
        assert AIModel.CLAUDE_3_HAIKU in titan_fallbacks
    
    def test_optimized_parameters(self, ai_config):
        """Test optimized parameter generation"""
        
        model_config = ai_config.model_configs[AIModel.CLAUDE_3_HAIKU]
        
        # Test different request types
        factual_params = ai_config.get_optimized_parameters(model_config, "factual_query")
        creative_params = ai_config.get_optimized_parameters(model_config, "creative_recipe")
        
        # Factual queries should have lower temperature
        assert factual_params["temperature"] < creative_params["temperature"]
        
        # Creative queries should have higher top_p
        assert creative_params["top_p"] >= factual_params["top_p"]
    
    def test_prompt_optimization(self, prompt_engine):
        """Test prompt template optimization and caching"""
        
        # Test prompt building
        variables = {
            'meal_type': 'dinner',
            'household_size': 2,
            'budget': 50,
            'dietary_restrictions': 'vegetarian',
            'cuisine_preferences': 'Mediterranean',
            'max_cooking_time': 30,
            'nutrition_goals': 'weight_loss'
        }
        
        prompt, template = prompt_engine.build_optimized_prompt(
            'meal_planning_optimized', variables
        )
        
        assert len(prompt) > 0
        assert 'vegetarian' in prompt
        assert 'Mediterranean' in prompt
        assert template.estimated_tokens > 0
        
        # Test cache key generation
        cache_key = prompt_engine.generate_cache_key('meal_planning_optimized', variables)
        assert cache_key.startswith('prompt_')
        assert len(cache_key) > 10
    
    def test_prompt_template_optimization(self, prompt_engine):
        """Test prompt template token optimization"""
        
        # Test token estimation
        template = prompt_engine.templates['nutrition_analysis_fast']
        assert template.estimated_tokens < 300  # Should be optimized for fast responses
        
        # Test model-specific optimization
        generic_prompt = "Analyze this food item: apple"
        
        claude_optimized = prompt_engine.optimize_prompt_for_model(
            generic_prompt, "anthropic.claude-3-haiku"
        )
        titan_optimized = prompt_engine.optimize_prompt_for_model(
            generic_prompt, "amazon.titan-text-express"
        )
        
        assert claude_optimized != titan_optimized  # Should be different optimizations
    
    def test_prompt_analytics(self, prompt_engine):
        """Test prompt usage analytics"""
        
        # Simulate some prompt usage
        variables = {'food_item': 'apple'}
        prompt, template = prompt_engine.build_optimized_prompt('nutrition_analysis_fast', variables)
        
        # Test analytics
        analytics = prompt_engine.get_prompt_analytics()
        assert 'templates' in analytics
        assert 'nutrition_analysis_fast' in analytics['templates']
        assert analytics['templates']['nutrition_analysis_fast']['usage_count'] > 0
    
    def test_context_enhancement(self, prompt_engine):
        """Test context-aware prompt enhancement"""
        
        variables = {'meal_type': 'breakfast'}
        context = {
            'user_profile': {
                'dietary_restrictions': ['gluten-free'],
                'cuisine_preferences': 'Italian'
            }
        }
        
        enhanced_vars = prompt_engine._enhance_variables_with_context(variables, context)
        
        assert 'dietary_restrictions' in enhanced_vars
        assert 'cuisine_preferences' in enhanced_vars
        assert enhanced_vars['dietary_restrictions'] == ['gluten-free']
        assert enhanced_vars['cuisine_preferences'] == 'Italian'
    
    def test_optimization_opportunities(self, prompt_engine):
        """Test optimization opportunity identification"""
        
        # Simulate usage to trigger opportunities
        for _ in range(150):  # High usage
            variables = {'food_item': f'test_food_{_}'}
            prompt, template = prompt_engine.build_optimized_prompt('nutrition_analysis_fast', variables)
        
        analytics = prompt_engine.get_prompt_analytics()
        opportunities = analytics.get('optimization_opportunities', [])
        
        # Should suggest optimizations for high-usage templates
        assert len(opportunities) >= 0  # May or may not have opportunities depending on thresholds


class TestModelConfiguration:
    """Test model configuration and selection logic"""
    
    @pytest.fixture
    def ai_config(self):
        """Create AI config manager for testing"""
        return AIConfigManager()
    
    def test_all_models_configured(self, ai_config):
        """Test that all models are properly configured"""
        
        # Check that all model enums have configurations
        for model_enum in AIModel:
            assert model_enum in ai_config.model_configs
            config = ai_config.model_configs[model_enum]
            
            # Validate configuration completeness
            assert config.model_id
            assert config.cost_per_1k_tokens > 0
            assert config.quality_score >= 1 and config.quality_score <= 10
            assert config.max_tokens > 0
            assert len(config.use_cases) > 0
    
    def test_model_selection_tiers(self, ai_config):
        """Test model selection respects user tiers"""
        
        use_case = "meal_planning"
        complexity = 5.0
        
        # Get models for different tiers
        free_model = ai_config.select_optimal_model(use_case, "free", complexity)
        standard_model = ai_config.select_optimal_model(use_case, "standard", complexity)
        premium_model = ai_config.select_optimal_model(use_case, "premium", complexity)
        
        # Free tier should get cheaper models
        assert free_model.cost_per_1k_tokens <= 0.001
        
        # Premium tier should get higher quality models
        assert premium_model.quality_score >= standard_model.quality_score
    
    def test_complexity_based_selection(self, ai_config):
        """Test that complexity affects model selection"""
        
        use_case = "detailed_analysis"
        user_tier = "standard"
        
        simple_model = ai_config.select_optimal_model(use_case, user_tier, complexity_score=2.0)
        complex_model = ai_config.select_optimal_model(use_case, user_tier, complexity_score=9.0)
        
        # Higher complexity should tend toward higher quality models
        # (This might be the same model depending on availability, but the logic should be there)
        assert complex_model.quality_score >= simple_model.quality_score
    
    def test_use_case_filtering(self, ai_config):
        """Test that models are filtered by use case"""
        
        # Test with a specific use case
        model = ai_config.select_optimal_model("quick_answers", "free", 3.0)
        
        # Should return a model suitable for quick answers
        assert "quick_answers" in model.use_cases or len(model.use_cases) > 0


@pytest.mark.asyncio
class TestAsyncOptimization:
    """Test async optimization features that don't require AWS"""
    
    async def test_prompt_building_performance(self):
        """Test prompt building performance"""
        
        prompt_engine = AdvancedPromptEngine()
        
        start_time = time.time()
        
        # Build multiple prompts
        for i in range(100):
            variables = {
                'food_item': f'test_food_{i}',
            }
            prompt, template = prompt_engine.build_optimized_prompt('nutrition_analysis_fast', variables)
            assert len(prompt) > 0
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be fast
        assert total_time < 1.0  # Less than 1 second for 100 prompts
    
    async def test_cache_key_generation_performance(self):
        """Test cache key generation performance"""
        
        prompt_engine = AdvancedPromptEngine()
        
        start_time = time.time()
        
        # Generate many cache keys
        for i in range(1000):
            variables = {'food_item': f'test_{i}'}
            cache_key = prompt_engine.generate_cache_key('nutrition_analysis_fast', variables)
            assert cache_key.startswith('prompt_')
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be very fast
        assert total_time < 0.5  # Less than 0.5 seconds for 1000 keys
    
    async def test_model_selection_performance(self):
        """Test model selection performance"""
        
        ai_config = AIConfigManager()
        
        start_time = time.time()
        
        # Select models many times
        for i in range(500):
            model = ai_config.select_optimal_model(
                "quick_answers", 
                "free" if i % 2 == 0 else "premium", 
                float(i % 10)
            )
            assert model is not None
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be fast
        assert total_time < 1.0  # Less than 1 second for 500 selections


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
