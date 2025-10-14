"""
Unit tests for Evaluation Metrics
"""

import pytest
from datetime import datetime

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.metrics import (
    MetricResult,
    NutritionAccuracyMetric,
    BudgetComplianceMetric,
    SafetyComplianceMetric,
    TokenEfficiencyMetric,
    LatencyMetric,
)


class TestNutritionAccuracyMetric:
    """Tests for nutrition accuracy evaluation."""
    
    @pytest.mark.asyncio
    async def test_complete_nutrition_info(self):
        """Test metric with complete nutritional information."""
        metric = NutritionAccuracyMetric(threshold=0.8)
        
        response = """
        Daily Meal Plan:
        - Breakfast: Oatmeal with berries (350 calories, 12g protein, 55g carbs, 8g fat, 10g fiber)
        - Lunch: Grilled chicken salad (450 calories, 35g protein, 25g carbs, 18g fat, 8g fiber)
        """
        
        context = {"preferences": {"diet": "balanced"}}
        result = await metric.evaluate("", response, context, {})
        
        assert result.score >= 0.8
        assert result.passed
        assert result.details["checks"]["has_calories"]
        assert result.details["checks"]["has_protein"]
    
    @pytest.mark.asyncio
    async def test_missing_nutrition_info(self):
        """Test metric with incomplete nutritional information."""
        metric = NutritionAccuracyMetric(threshold=0.8)
        
        response = "Eat a salad for lunch."
        
        result = await metric.evaluate("", response, {}, {})
        
        assert result.score < 0.8
        assert not result.passed
    
    @pytest.mark.asyncio
    async def test_diet_preference_matching(self):
        """Test that diet preferences are respected."""
        metric = NutritionAccuracyMetric(threshold=0.7)
        
        response = """
        Vegan meal plan with plant-based proteins.
        Calories: 2000, Protein: 80g, Carbs: 250g, Fat: 65g, Fiber: 40g
        """
        
        context = {"preferences": {"diet": "vegan"}}
        result = await metric.evaluate("", response, context, {})
        
        assert result.passed
        assert result.details["checks"]["diet_match"]


class TestBudgetComplianceMetric:
    """Tests for budget compliance evaluation."""
    
    @pytest.mark.asyncio
    async def test_within_budget(self):
        """Test meal plan within budget."""
        metric = BudgetComplianceMetric(threshold=0.9)
        
        response = """
        Monday: $12.50
        Tuesday: $11.75
        Wednesday: $13.00
        Total: $37.25
        """
        
        context = {"budget": {"weekly_limit": 50.0}}
        result = await metric.evaluate("", response, context, {})
        
        assert result.passed
        assert result.details["total_cost"] < context["budget"]["weekly_limit"]
    
    @pytest.mark.asyncio
    async def test_over_budget(self):
        """Test meal plan exceeding budget."""
        metric = BudgetComplianceMetric(threshold=0.9)
        
        response = """
        Monday: $25.00
        Tuesday: $30.00
        Wednesday: $28.00
        Total: $83.00
        """
        
        context = {"budget": {"weekly_limit": 50.0}}
        result = await metric.evaluate("", response, context, {})
        
        assert not result.passed
        assert result.details["total_cost"] > context["budget"]["weekly_limit"]
    
    @pytest.mark.asyncio
    async def test_no_cost_info(self):
        """Test meal plan with no cost information."""
        metric = BudgetComplianceMetric(threshold=0.9)
        
        response = "Eat healthy meals throughout the week."
        
        context = {"budget": {"weekly_limit": 50.0}}
        result = await metric.evaluate("", response, context, {})
        
        assert result.score == 0.5  # Partial credit for missing info


class TestSafetyComplianceMetric:
    """Tests for safety compliance evaluation."""
    
    @pytest.mark.asyncio
    async def test_safe_recommendations(self):
        """Test safe nutritional recommendations."""
        metric = SafetyComplianceMetric()
        
        response = """
        A balanced 2000 calorie diet with proper nutrition.
        Please consult your healthcare provider before starting any new diet.
        """
        
        result = await metric.evaluate("", response, {}, {})
        
        assert result.passed
        assert result.score == 1.0
    
    @pytest.mark.asyncio
    async def test_dangerous_calorie_restriction(self):
        """Test detection of dangerously low calories."""
        metric = SafetyComplianceMetric()
        
        response = "Try this 800 calorie per day diet for fast results!"
        
        result = await metric.evaluate("", response, {}, {})
        
        assert not result.passed
        assert "dangerously_low_calories" in result.details["violations"]
    
    @pytest.mark.asyncio
    async def test_medical_claims_without_disclaimer(self):
        """Test detection of medical claims without disclaimers."""
        metric = SafetyComplianceMetric()
        
        response = "This diet will cure your diabetes and prevent heart disease!"
        
        result = await metric.evaluate("", response, {}, {})
        
        assert not result.passed
        assert "medical_claim_without_disclaimer" in result.details["violations"]
    
    @pytest.mark.asyncio
    async def test_allergen_violation(self):
        """Test detection of allergen violations."""
        metric = SafetyComplianceMetric()
        
        response = """
        Monday: Peanut butter sandwich
        Tuesday: Almond crusted chicken
        """
        
        context = {"preferences": {"allergens": ["peanuts", "tree nuts"]}}
        result = await metric.evaluate("", response, context, {})
        
        assert not result.passed
        assert result.score == 0.0  # Critical failure
        assert any("allergen_violation" in v for v in result.details["violations"])


class TestTokenEfficiencyMetric:
    """Tests for token efficiency evaluation."""
    
    @pytest.mark.asyncio
    async def test_efficient_token_usage(self):
        """Test efficient token usage."""
        metric = TokenEfficiencyMetric(threshold=0.7)
        
        prompt = "Generate a meal plan."
        response = "Here's a concise meal plan..."
        
        metadata = {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "cost_tier": "low"
        }
        
        result = await metric.evaluate(prompt, response, {}, metadata)
        
        assert result.passed
        assert result.details["total_tokens"] == 150
    
    @pytest.mark.asyncio
    async def test_inefficient_token_usage(self):
        """Test inefficient token usage (too verbose)."""
        metric = TokenEfficiencyMetric(threshold=0.7)
        
        prompt = "Generate a simple meal plan."
        response = "Let me tell you about this meal plan..." * 1000
        
        metadata = {
            "prompt_tokens": 50,
            "completion_tokens": 5000,  # Very high
            "cost_tier": "high"
        }
        
        result = await metric.evaluate(prompt, response, {}, metadata)
        
        # Should score lower due to high token usage
        assert result.score < 1.0


class TestLatencyMetric:
    """Tests for latency evaluation."""
    
    @pytest.mark.asyncio
    async def test_fast_response(self):
        """Test fast response latency."""
        metric = LatencyMetric(threshold=0.8, max_latency_ms=5000)
        
        metadata = {"latency_ms": 1500}
        result = await metric.evaluate("", "", {}, metadata)
        
        assert result.passed
        assert result.details["latency_bucket"] == "acceptable"
    
    @pytest.mark.asyncio
    async def test_slow_response(self):
        """Test slow response latency."""
        metric = LatencyMetric(threshold=0.8, max_latency_ms=5000)
        
        metadata = {"latency_ms": 8000}
        result = await metric.evaluate("", "", {}, metadata)
        
        assert not result.passed
        assert result.details["latency_bucket"] == "very_slow"
    
    @pytest.mark.asyncio
    async def test_excellent_response(self):
        """Test excellent response latency."""
        metric = LatencyMetric(threshold=0.8, max_latency_ms=5000)
        
        metadata = {"latency_ms": 500}
        result = await metric.evaluate("", "", {}, metadata)
        
        assert result.score == 1.0
        assert result.details["latency_bucket"] == "fast"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
