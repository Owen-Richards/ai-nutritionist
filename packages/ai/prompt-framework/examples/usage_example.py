"""
Example usage of the AI Prompt Framework

Demonstrates template rendering, evaluation, and A/B testing.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.templates.base import PromptRenderer
from src.evaluation.harness import PromptEvaluator
from src.evaluation.metrics import (
    NutritionAccuracyMetric,
    BudgetComplianceMetric,
    SafetyComplianceMetric,
    TokenEfficiencyMetric,
    LatencyMetric,
)


async def mock_llm_call(prompt: str) -> dict:
    """
    Mock LLM call for demonstration purposes.
    
    In production, this would call AWS Bedrock or similar.
    """
    # Simulate a realistic response
    response = """
    {
      "week_summary": {
        "total_cost": 75.50,
        "avg_daily_calories": 1985,
        "dietary_compliance": "vegan"
      },
      "daily_plans": [
        {
          "day": "Monday",
          "meals": [
            {
              "type": "breakfast",
              "name": "Oatmeal with Berries",
              "recipe": "Cook 1/2 cup oats with almond milk, top with mixed berries",
              "ingredients": [
                {"item": "Rolled oats", "amount": "1/2 cup", "cost": 0.50},
                {"item": "Almond milk", "amount": "1 cup", "cost": 0.75},
                {"item": "Mixed berries", "amount": "1/2 cup", "cost": 2.00}
              ],
              "nutrition": {
                "calories": 320,
                "protein_g": 8,
                "carbs_g": 58,
                "fat_g": 6,
                "fiber_g": 10
              }
            }
          ],
          "daily_totals": {"calories": 1950, "cost": 10.75}
        }
      ],
      "grocery_list": {
        "grains": [
          {"item": "Rolled oats", "quantity": "2 lbs", "cost": 5.00}
        ],
        "produce": [
          {"item": "Mixed berries", "quantity": "3 containers", "cost": 12.00}
        ]
      }
    }
    
    ⚠️ Disclaimer: Please consult with a healthcare provider before making 
    significant dietary changes.
    """
    
    # Simulate metadata
    metadata = {
        "prompt_tokens": 150,
        "completion_tokens": 450,
        "latency_ms": 2800,
        "cost_tier": "medium"
    }
    
    return {
        "response": response,
        "metadata": metadata
    }


async def example_basic_rendering():
    """Example 1: Basic template rendering."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Template Rendering")
    print("="*60)
    
    # Get template directory (one level up from examples/)
    template_dir = Path(__file__).parent.parent / "templates"
    
    # Initialize renderer
    renderer = PromptRenderer(template_dir)
    
    # Define context
    context = {
        "preferences": {
            "diet": "vegan",
            "daily_calories": 2000,
            "allergens": ["peanuts"],
            "dislikes": ["mushrooms"]
        },
        "budget": {
            "weekly_limit": 80
        }
    }
    
    # Render template
    prompt = await renderer.render(
        name="meal_plan_weekly",
        version="1.0.0",
        context=context
    )
    
    print(f"\n✅ Rendered prompt ({len(prompt)} characters):")
    print("-" * 60)
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("-" * 60)


async def example_evaluation():
    """Example 2: Evaluating a prompt-response pair."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Prompt Evaluation")
    print("="*60)
    
    # Setup
    template_dir = Path(__file__).parent.parent / "templates"
    renderer = PromptRenderer(template_dir)
    
    context = {
        "preferences": {"diet": "vegan", "daily_calories": 2000},
        "budget": {"weekly_limit": 80}
    }
    
    # Render prompt
    prompt = await renderer.render("meal_plan_weekly", "1.0.0", context)
    
    # Get LLM response (mocked)
    llm_result = await mock_llm_call(prompt)
    
    # Setup evaluator
    evaluator = PromptEvaluator()
    evaluator.add_metric(NutritionAccuracyMetric(threshold=0.8), weight=2.0)
    evaluator.add_metric(BudgetComplianceMetric(threshold=0.9), weight=1.5)
    evaluator.add_metric(SafetyComplianceMetric(threshold=1.0), weight=3.0)
    evaluator.add_metric(TokenEfficiencyMetric(threshold=0.7), weight=1.0)
    evaluator.add_metric(LatencyMetric(threshold=0.8), weight=1.0)
    
    # Evaluate
    template = renderer.load_template("meal_plan_weekly", "1.0.0")
    report = await evaluator.evaluate(
        prompt_name="meal_plan_weekly",
        prompt_version="1.0.0",
        prompt_hash=template.template_hash,
        test_context=context,
        rendered_prompt=prompt,
        llm_response=llm_result["response"],
        llm_metadata=llm_result["metadata"]
    )
    
    # Display report
    print(report.summary())
    
    # Detailed metrics
    print("\n📊 Detailed Metric Breakdown:")
    for result in report.metric_results:
        print(f"\n{result.metric_name}:")
        print(f"  Score: {result.score:.2%}")
        print(f"  Passed: {'✅' if result.passed else '❌'}")
        if result.details:
            print(f"  Details: {result.details}")


async def example_ab_testing():
    """Example 3: A/B testing two prompt versions."""
    print("\n" + "="*60)
    print("EXAMPLE 3: A/B Testing Prompt Versions")
    print("="*60)
    
    # Setup
    template_dir = Path(__file__).parent.parent / "templates"
    renderer = PromptRenderer(template_dir)
    
    evaluator = PromptEvaluator()
    evaluator.add_metric(NutritionAccuracyMetric(), weight=2.0)
    evaluator.add_metric(BudgetComplianceMetric(), weight=1.5)
    evaluator.add_metric(SafetyComplianceMetric(), weight=3.0)
    
    context = {
        "preferences": {"diet": "vegan", "daily_calories": 2000},
        "budget": {"weekly_limit": 80}
    }
    
    # Compare versions (if 2.0.0 exists)
    versions = renderer.list_versions("meal_plan_weekly")
    print(f"\nAvailable versions: {versions}")
    
    if len(versions) >= 2:
        reports = await evaluator.compare_versions(
            prompt_name="meal_plan_weekly",
            version_a=versions[0],
            version_b=versions[1],
            test_context=context,
            renderer=renderer,
            llm_fn=mock_llm_call
        )
        
        # Compare results
        print(f"\n📊 A/B Test Results:")
        print(f"{'Version':<12} {'Score':<10} {'Pass Rate':<12} {'Status'}")
        print("-" * 60)
        
        for version, report in reports.items():
            status = "✅ PASSED" if report.passed else "❌ FAILED"
            pass_rate = report.passed_metrics / report.total_metrics
            print(f"{version:<12} {report.overall_score:<10.2%} {pass_rate:<12.2%} {status}")
        
        # Recommendation
        best_version = max(reports.items(), key=lambda x: x[1].overall_score)[0]
        print(f"\n🏆 Recommended version: {best_version}")
    else:
        print("\n⚠️  Only one version available. Create version 2.0.0 for A/B testing.")


async def example_batch_evaluation():
    """Example 4: Batch evaluation across multiple test cases."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Batch Evaluation")
    print("="*60)
    
    # Setup
    template_dir = Path(__file__).parent.parent / "templates"
    renderer = PromptRenderer(template_dir)
    
    evaluator = PromptEvaluator()
    evaluator.add_metric(NutritionAccuracyMetric(), weight=2.0)
    evaluator.add_metric(BudgetComplianceMetric(), weight=1.5)
    evaluator.add_metric(SafetyComplianceMetric(), weight=3.0)
    
    # Define test cases
    test_cases = [
        {
            "preferences": {"diet": "vegan", "daily_calories": 2000},
            "budget": {"weekly_limit": 80}
        },
        {
            "preferences": {"diet": "keto", "daily_calories": 1800},
            "budget": {"weekly_limit": 100}
        },
        {
            "preferences": {"diet": "balanced", "daily_calories": 2200, "allergens": ["gluten"]},
            "budget": {"weekly_limit": 60}
        }
    ]
    
    print(f"\n📝 Running {len(test_cases)} test cases...")
    
    # Batch evaluate
    reports = await evaluator.batch_evaluate(
        prompt_name="meal_plan_weekly",
        prompt_version="1.0.0",
        test_cases=test_cases,
        renderer=renderer,
        llm_fn=mock_llm_call
    )
    
    # Aggregate statistics
    stats = evaluator.aggregate_reports(reports)
    
    print(f"\n📊 Aggregate Statistics:")
    print(f"  Total evaluations: {stats['total_evaluations']}")
    print(f"  Passed: {stats['passed_evaluations']}")
    print(f"  Pass rate: {stats['pass_rate']:.2%}")
    print(f"  Average score: {stats['average_overall_score']:.2%}")
    print(f"  Score range: {stats['min_score']:.2%} - {stats['max_score']:.2%}")
    
    print(f"\n📊 Average Metric Scores:")
    for metric_name, avg_score in stats['average_metric_scores'].items():
        print(f"  {metric_name}: {avg_score:.2%}")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("AI Prompt Framework Examples")
    print("="*60)
    
    try:
        await example_basic_rendering()
        await example_evaluation()
        await example_ab_testing()
        await example_batch_evaluation()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
