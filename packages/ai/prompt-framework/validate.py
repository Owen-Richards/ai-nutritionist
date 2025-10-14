"""
Quick validation script for Prompt Framework
Tests basic functionality without emojis for Windows compatibility
"""

import asyncio
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.templates.base import PromptRenderer
from src.evaluation.harness import PromptEvaluator
from src.evaluation.metrics import NutritionAccuracyMetric, SafetyComplianceMetric


async def main():
    print("\n" + "="*60)
    print("Prompt Framework Validation")
    print("="*60)
    
    # 1. Test template loading
    print("\n[1/4] Testing template loading...")
    template_dir = Path(__file__).parent / "templates"
    print(f"   Looking in: {template_dir}")
    renderer = PromptRenderer(template_dir)
    versions = renderer.list_versions("meal_plan_weekly")
    print(f"   PASS - Found {len(versions)} version(s): {versions}")
    
    # 2. Test template rendering
    print("\n[2/4] Testing template rendering...")
    context = {
        "preferences": {
            "diet": "vegan",
            "daily_calories": 2000,
            "allergens": [],
            "dislikes": []
        },
        "budget": {"weekly_limit": 80}
    }
    prompt = await renderer.render("meal_plan_weekly", "1.0.0", context)
    print(f"   PASS - Rendered {len(prompt)} character prompt")
    
    # 3. Test evaluator setup
    print("\n[3/4] Testing evaluator setup...")
    evaluator = PromptEvaluator()
    evaluator.add_metric(NutritionAccuracyMetric(), weight=2.0)
    evaluator.add_metric(SafetyComplianceMetric(), weight=3.0)
    print(f"   PASS - Added {len(evaluator.metrics)} metrics")
    
    # 4. Test evaluation (with mock response)
    print("\n[4/4] Testing evaluation...")
    mock_response = """
    {
      "week_summary": {
        "total_cost": 75.50,
        "avg_daily_calories": 1985
      },
      "daily_plans": [
        {
          "day": "Monday",
          "meals": [
            {
              "type": "breakfast",
              "name": "Oatmeal with Berries",
              "nutrition": {
                "calories": 320,
                "protein_g": 8,
                "carbs_g": 58,
                "fat_g": 6,
                "fiber_g": 10
              }
            }
          ]
        }
      ]
    }
    
    Disclaimer: Please consult with a healthcare provider.
    """
    
    template = renderer.load_template("meal_plan_weekly", "1.0.0")
    report = await evaluator.evaluate(
        prompt_name="meal_plan_weekly",
        prompt_version="1.0.0",
        prompt_hash=template.template_hash,
        test_context=context,
        rendered_prompt=prompt,
        llm_response=mock_response,
        llm_metadata={"prompt_tokens": 150, "completion_tokens": 450}
    )
    
    status = "PASSED" if report.passed else "FAILED"
    print(f"   {status} - Overall score: {report.overall_score:.2%}")
    print(f"   Metrics: {report.passed_metrics}/{report.total_metrics} passed")
    
    print("\n" + "="*60)
    print("All validation checks completed successfully!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
