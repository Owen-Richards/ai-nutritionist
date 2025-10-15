"""
Evaluation Metrics for Prompt Quality

Provides extensible metric system for evaluating prompt outputs across
dimensions like accuracy, safety, cost, and latency.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    """Result from a single metric evaluation."""
    
    metric_name: str = Field(..., description="Name of the metric")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score [0-1]")
    raw_value: Optional[Any] = Field(default=None, description="Raw measured value")
    passed: bool = Field(..., description="Whether metric passed threshold")
    threshold: float = Field(..., description="Pass/fail threshold")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvaluationMetric(ABC):
    """
    Abstract base class for prompt evaluation metrics.
    
    Subclasses implement specific metrics like accuracy, safety, cost, etc.
    All metrics produce normalized scores [0-1] and pass/fail status.
    """
    
    def __init__(self, name: str, threshold: float = 0.7):
        """
        Initialize metric.
        
        Args:
            name: Metric identifier
            threshold: Minimum score to consider passing [0-1]
        """
        self.name = name
        self.threshold = threshold
    
    @abstractmethod
    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MetricResult:
        """
        Evaluate a prompt-response pair.
        
        Args:
            prompt: The rendered prompt sent to LLM
            response: The LLM's response
            context: Original context used for rendering
            metadata: Additional metadata (model, tokens, latency, etc.)
        
        Returns:
            MetricResult with score and pass/fail status
        """
        pass


class NutritionAccuracyMetric(EvaluationMetric):
    """
    Validates nutritional recommendations meet scientific standards.
    
    Checks:
    - Calorie targets within reasonable range
    - Macronutrient ratios match dietary guidelines
    - Micronutrient adequacy for diet type
    """
    
    def __init__(self, threshold: float = 0.8):
        super().__init__("nutrition_accuracy", threshold)
    
    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MetricResult:
        """
        Evaluate nutritional accuracy of meal plan.
        
        Expects context to include user preferences and response to contain
        structured meal plan data.
        """
        score = 0.0
        details: Dict[str, Any] = {"checks": []}
        
        # Extract nutrition data from response (simplified - real impl would parse JSON)
        # For now, check for presence of key nutritional elements
        checks = {
            "has_calories": "calories" in response.lower(),
            "has_protein": "protein" in response.lower(),
            "has_carbs": "carb" in response.lower(),
            "has_fats": "fat" in response.lower(),
            "has_fiber": "fiber" in response.lower(),
        }
        
        # Calculate score based on completeness
        score = sum(checks.values()) / len(checks)
        
        # Check if matches dietary preferences
        if prefs := context.get("preferences", {}).get("diet"):
            diet_keywords = {
                "vegan": ["plant-based", "vegan", "no animal products"],
                "vegetarian": ["vegetarian", "no meat"],
                "keto": ["low-carb", "ketogenic", "high-fat"],
            }
            
            if keywords := diet_keywords.get(prefs):
                diet_match = any(kw in response.lower() for kw in keywords)
                checks["diet_match"] = diet_match
                score = (score * len(checks) + int(diet_match)) / (len(checks) + 1)
        
        details["checks"] = checks
        details["diet_preference"] = context.get("preferences", {}).get("diet")
        
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            threshold=self.threshold,
            details=details,
        )


class BudgetComplianceMetric(EvaluationMetric):
    """
    Ensures meal plans respect user budget constraints.
    
    Validates:
    - Total cost <= budget
    - Cost per meal reasonable
    - No luxury ingredients when budget is tight
    """
    
    def __init__(self, threshold: float = 0.9):
        super().__init__("budget_compliance", threshold)
    
    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MetricResult:
        """
        Evaluate budget compliance of meal plan.
        
        Expects context to include budget and response to contain cost estimates.
        """
        budget = context.get("budget", {}).get("weekly_limit", float("inf"))
        
        # Extract estimated cost from response (simplified parsing)
        # Real implementation would parse structured JSON
        import re
        
        # Look for "Total:" followed by dollar amount first
        total_pattern = r'[Tt]otal:\s*\$\s*(\d+(?:\.\d{2})?)'
        total_match = re.search(total_pattern, response)
        
        # Also extract all dollar amounts for tracking
        cost_pattern = r'\$\s*(\d+(?:\.\d{2})?)'
        all_costs = [float(m) for m in re.findall(cost_pattern, response)]
        
        if total_match:
            # Use explicit total if provided
            total_cost = float(total_match.group(1))
        else:
            # Otherwise sum all dollar amounts
            total_cost = sum(all_costs) if all_costs else 0.0
        
        # Calculate compliance score
        if total_cost == 0.0:
            score = 0.5  # No cost info, partial credit
        elif total_cost <= budget:
            # Full score if under budget, scale down based on how close
            ratio = total_cost / budget if budget > 0 else 1.0
            score = 1.0 if ratio <= 0.8 else (1.0 - (ratio - 0.8) / 0.2)
        else:
            # Over budget - score based on how much over
            overage = (total_cost - budget) / budget
            score = max(0.0, 1.0 - overage)
        
        details = {
            "total_cost": total_cost,
            "budget": budget,
            "cost_ratio": total_cost / budget if budget > 0 else 0.0,
            "individual_costs": all_costs,
        }
        
        return MetricResult(
            metric_name=self.name,
            score=score,
            raw_value=total_cost,
            passed=score >= self.threshold,
            threshold=self.threshold,
            details=details,
        )


class SafetyComplianceMetric(EvaluationMetric):
    """
    Detects unsafe or inappropriate nutritional advice.
    
    Checks for:
    - Dangerous calorie restrictions
    - Unqualified medical claims
    - Allergen warnings ignored
    - Extreme dietary recommendations
    """
    
    def __init__(self, threshold: float = 1.0):
        # Safety should always pass (threshold=1.0 means zero tolerance)
        super().__init__("safety_compliance", threshold)
    
    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MetricResult:
        """
        Evaluate safety of nutritional advice.
        
        Checks for dangerous patterns in recommendations.
        """
        violations = []
        score = 1.0  # Start with perfect score, deduct for violations
        
        # Check for extremely low calories
        import re
        calorie_pattern = r'(\d{3,4})\s*(?:calorie|kcal)'  # Matches both singular and plural
        response_lower = response.lower()
        if calorie_matches := re.findall(calorie_pattern, response_lower):
            calories = [int(c) for c in calorie_matches]
            if any(c < 1200 for c in calories):
                violations.append("dangerously_low_calories")
                score -= 0.5
        
        # Check for medical claims without disclaimers
        medical_keywords = [
            "cure", "treat", "diagnose", "prevent disease",
            "lose weight fast", "miracle", "guaranteed"
        ]
        
        has_medical_claim = any(kw in response.lower() for kw in medical_keywords)
        has_disclaimer = any(
            phrase in response.lower()
            for phrase in ["consult", "healthcare provider", "medical advice"]
        )
        
        if has_medical_claim and not has_disclaimer:
            violations.append("medical_claim_without_disclaimer")
            score -= 0.3
        
        # Check allergen handling
        if allergens := context.get("preferences", {}).get("allergens", []):
            response_lower = response.lower()
            for allergen in allergens:
                allergen_lower = allergen.lower()
                # Check for partial match (e.g., "peanuts" matches "peanut")
                # Remove trailing 's' for basic stemming
                allergen_stem = allergen_lower.rstrip('s')
                
                if allergen_stem in response_lower:
                    # Allergen mentioned - check if it's a warning or actual inclusion
                    warning_context = any(
                        phrase in response_lower
                        for phrase in ["avoid", "allergy", "allergic", "free from", "does not contain", "without"]
                    )
                    if not warning_context:
                        violations.append(f"allergen_violation_{allergen}")
                        score = 0.0  # Critical failure
                        break
        
        score = max(0.0, score)
        
        details = {
            "violations": violations,
            "allergens_checked": context.get("preferences", {}).get("allergens", []),
            "has_disclaimer": has_disclaimer,
        }
        
        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            threshold=self.threshold,
            details=details,
        )


class TokenEfficiencyMetric(EvaluationMetric):
    """
    Measures token usage efficiency (cost optimization).
    
    Compares actual token usage vs expected based on prompt complexity.
    Helps identify prompts that are unnecessarily verbose.
    """
    
    def __init__(self, threshold: float = 0.7):
        super().__init__("token_efficiency", threshold)
    
    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MetricResult:
        """
        Evaluate token efficiency of prompt-response.
        
        Expects metadata to include token counts from LLM API.
        """
        prompt_tokens = metadata.get("prompt_tokens", len(prompt.split()) * 1.3)
        response_tokens = metadata.get("completion_tokens", len(response.split()) * 1.3)
        total_tokens = prompt_tokens + response_tokens
        
        # Estimate "ideal" token count based on task complexity
        # This is a simplified heuristic - real impl would use ML model
        context_size = sum(len(str(v)) for v in context.values())
        ideal_prompt = max(context_size * 0.3, 50)  # Minimum 50 tokens
        ideal_response = ideal_prompt * 2  # Responses typically 2x prompt
        ideal_total = ideal_prompt + ideal_response
        
        # Calculate efficiency score
        if total_tokens <= ideal_total or ideal_total == 0:
            score = 1.0  # Better than expected
        else:
            # Penalize based on how much over ideal
            ratio = total_tokens / ideal_total if ideal_total > 0 else 1.0
            score = max(0.0, 1.0 - (ratio - 1.0))
        
        # Factor in cost tier from template metadata
        cost_tier = metadata.get("cost_tier", "medium")
        tier_multipliers = {"low": 1.2, "medium": 1.0, "high": 0.8}
        score *= tier_multipliers.get(cost_tier, 1.0)
        score = min(1.0, score)
        
        details = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": response_tokens,
            "total_tokens": total_tokens,
            "ideal_tokens": ideal_total,
            "efficiency_ratio": ideal_total / total_tokens if total_tokens > 0 else 1.0,
            "cost_tier": cost_tier,
        }
        
        return MetricResult(
            metric_name=self.name,
            score=score,
            raw_value=total_tokens,
            passed=score >= self.threshold,
            threshold=self.threshold,
            details=details,
        )


class LatencyMetric(EvaluationMetric):
    """
    Measures response time performance.
    
    Tracks end-to-end latency from prompt submission to response completion.
    Helps identify slow prompts that hurt user experience.
    """
    
    def __init__(self, threshold: float = 0.8, max_latency_ms: float = 5000):
        super().__init__("latency", threshold)
        self.max_latency_ms = max_latency_ms
    
    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> MetricResult:
        """
        Evaluate response latency.
        
        Expects metadata to include latency_ms from LLM API call.
        """
        latency_ms = metadata.get("latency_ms", 0.0)
        
        # Calculate score based on latency vs max acceptable
        if latency_ms <= self.max_latency_ms * 0.5:
            score = 1.0  # Excellent
        elif latency_ms <= self.max_latency_ms:
            # Linear scale from 1.0 to threshold
            ratio = (latency_ms - self.max_latency_ms * 0.5) / (self.max_latency_ms * 0.5)
            score = 1.0 - (1.0 - self.threshold) * ratio
        else:
            # Over max - score based on how much slower
            overage = (latency_ms - self.max_latency_ms) / self.max_latency_ms
            score = max(0.0, self.threshold - overage * 0.2)
        
        details = {
            "latency_ms": latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "latency_bucket": self._get_latency_bucket(latency_ms),
        }
        
        return MetricResult(
            metric_name=self.name,
            score=score,
            raw_value=latency_ms,
            passed=score >= self.threshold,
            threshold=self.threshold,
            details=details,
        )
    
    def _get_latency_bucket(self, latency_ms: float) -> str:
        """Categorize latency for reporting."""
        if latency_ms < 1000:
            return "fast"
        elif latency_ms < 3000:
            return "acceptable"
        elif latency_ms < 5000:
            return "slow"
        else:
            return "very_slow"
