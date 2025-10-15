"""
AI Prompt Framework Package

AI_CONTEXT
Purpose: Structured prompt engineering with versioning, evaluation, and cost tracking
Public API: PromptTemplate, PromptRenderer, PromptEvaluator, EvaluationMetric
Internal: Template caching, Jinja2 rendering engine
Contracts: Async rendering, thread-safe caching, Pydantic validation
Side Effects: File system access for templates, AWS Bedrock API calls during evaluation
Stability: public - New framework for systematic prompt management
Usage Example:
    from packages.ai.prompt_framework import PromptRenderer, PromptTemplate
    
    renderer = PromptRenderer("templates/")
    prompt = await renderer.render(
        "meal_plan_weekly",
        "1.0.0",
        {"preferences": {"diet": "vegan"}}
    )
"""

from .templates.base import PromptTemplate, PromptRenderer
from .evaluation.harness import PromptEvaluator, EvaluationReport
from .evaluation.metrics import (
    EvaluationMetric,
    NutritionAccuracyMetric,
    BudgetComplianceMetric,
    SafetyComplianceMetric
)

__all__ = [
    "PromptTemplate",
    "PromptRenderer",
    "PromptEvaluator",
    "EvaluationReport",
    "EvaluationMetric",
    "NutritionAccuracyMetric",
    "BudgetComplianceMetric",
    "SafetyComplianceMetric",
]

__version__ = "1.0.0"
