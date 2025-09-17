"""Rule-based meal plan engine used for the HTTP orchestration layer."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .models import DraftMeal, PlanDraft, PlanGenerationCommand, PlanFeedbackCommand


@dataclass
class RuleBasedMealPlanEngine:
    """Deterministic meal plan generator that respects basic preferences."""

    _feedback_tracker: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))

    def generate(self, command: PlanGenerationCommand) -> PlanDraft:
        library_by_type = _get_library_grouped()
        filtered_library = {
            meal_type: _filter_meals(meals, command.preferences)
            for meal_type, meals in library_by_type.items()
        }

        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        meal_order = ["breakfast", "lunch", "dinner"]
        plan_meals: List[DraftMeal] = []
        seed = int(
            hashlib.sha256(
                f"{command.user_id}-{command.week_start.isoformat()}".encode("utf-8")
            ).hexdigest(),
            16,
        )

        for day_index, day_name in enumerate(days):
            for meal_index, meal_type in enumerate(meal_order):
                candidates = filtered_library.get(meal_type) or library_by_type[meal_type]
                meal = _pick_meal(candidates, seed, day_index, meal_index)
                plan_meals.append(
                    DraftMeal(
                        day=day_name,
                        meal_type=meal_type,
                        title=meal["title"],
                        description=meal["description"],
                        ingredients=list(meal["ingredients"]),
                        calories=int(meal["calories"]),
                        prep_minutes=int(meal["prep_minutes"]),
                        cost=float(meal["cost"]),
                        macros=dict(meal["macros"]),
                        tags=list(meal.get("tags", [])),
                    )
                )

        estimated_cost = sum(meal.cost for meal in plan_meals)
        total_protein = sum(meal.macros.get("protein", 0.0) for meal in plan_meals)
        total_carbs = sum(meal.macros.get("carbs", 0.0) for meal in plan_meals)
        total_fat = sum(meal.macros.get("fat", 0.0) for meal in plan_meals)

        macro_summary = {
            "protein": round(total_protein, 1),
            "carbs": round(total_carbs, 1),
            "fat": round(total_fat, 1),
            "calories": sum(meal.calories for meal in plan_meals),
        }

        notes: List[str] = []
        warnings: List[str] = []

        if command.preferences.diet:
            notes.append(f"Dietary focus: {command.preferences.diet}")
        if command.preferences.budget_limit is not None:
            if estimated_cost <= command.preferences.budget_limit:
                notes.append("Plan meets weekly budget target.")
            else:
                overage = estimated_cost - command.preferences.budget_limit
                warnings.append(
                    f"Plan exceeds budget by ${overage:.2f}. Consider swapping lower-cost options."
                )
        if command.preferences.max_prep_minutes:
            notes.append(
                f"Prep time capped at {command.preferences.max_prep_minutes} minutes per meal."
            )

        return PlanDraft(
            meals=plan_meals,
            estimated_cost=round(estimated_cost, 2),
            macro_summary=macro_summary,
            notes=notes,
            warnings=warnings,
        )

    def ingest_feedback(self, feedback: PlanFeedbackCommand) -> None:
        """Track feedback counts to inform future heuristics."""

        tally = self._feedback_tracker[feedback.user_id]
        bucket = "high" if feedback.rating >= 4 else ("low" if feedback.rating <= 2 else "medium")
        tally[bucket] += 1


# --- Internal helpers ----------------------------------------------------


def _get_library_grouped() -> Dict[str, List[Dict[str, object]]]:
    grouped: Dict[str, List[Dict[str, object]]] = {"breakfast": [], "lunch": [], "dinner": []}
    for meal in _MEAL_LIBRARY:
        grouped[meal["meal_type"]].append(meal)
    return grouped


def _filter_meals(meals: Iterable[Dict[str, object]], preferences) -> List[Dict[str, object]]:
    filtered: List[Dict[str, object]] = []
    for candidate in meals:
        if not _supports_diet(candidate, preferences.diet):
            continue
        if not _respects_prep_time(candidate, preferences.max_prep_minutes):
            continue
        if _contains_blocked_ingredient(candidate, preferences.allergies, preferences.avoid_ingredients):
            continue
        filtered.append(candidate)
    return filtered


def _supports_diet(meal: Dict[str, object], diet: str | None) -> bool:
    if not diet or diet.lower() in {"any", "omnivore"}:
        return True
    tags = {tag.lower() for tag in meal.get("tags", [])}
    diet_lower = diet.lower()
    if diet_lower == "vegetarian":
        return "vegetarian" in tags or "vegan" in tags
    if diet_lower == "vegan":
        return "vegan" in tags
    if diet_lower == "pescatarian":
        return "pescatarian" in tags or "seafood" in tags
    if diet_lower in {"gluten_free", "gluten-free"}:
        return "gluten_free" in tags
    if diet_lower == "mediterranean":
        return "mediterranean" in tags or "vegetarian" in tags or "pescatarian" in tags
    return True


def _respects_prep_time(meal: Dict[str, object], max_minutes: int | None) -> bool:
    if not max_minutes:
        return True
    return int(meal.get("prep_minutes", 0)) <= max_minutes


def _contains_blocked_ingredient(
    meal: Dict[str, object], allergies: Iterable[str], avoid_list: Iterable[str]
) -> bool:
    lowered_ingredients = [ingredient.lower() for ingredient in meal.get("ingredients", [])]
    blocked = {item.lower() for item in allergies or []} | {item.lower() for item in avoid_list or []}
    return any(blocked_item in ingredient for blocked_item in blocked for ingredient in lowered_ingredients)


def _pick_meal(
    meals: List[Dict[str, object]], seed: int, day_index: int, meal_index: int
) -> Dict[str, object]:
    if not meals:
        raise ValueError("Meal library cannot be empty")
    offset = (seed + day_index * 7 + meal_index * 3) % len(meals)
    return meals[offset]


# --- Static meal library --------------------------------------------------

_MEAL_LIBRARY: List[Dict[str, object]] = [
    {
        "meal_type": "breakfast",
        "title": "Greek Yogurt Parfait",
        "description": "Greek yogurt layered with berries, chia, and granola.",
        "ingredients": ["greek yogurt", "blueberries", "strawberries", "chia seeds", "granola"],
        "calories": 380,
        "prep_minutes": 10,
        "cost": 2.40,
        "macros": {"protein": 24, "carbs": 48, "fat": 10},
        "tags": ["vegetarian", "gluten_optional"],
    },
    {
        "meal_type": "breakfast",
        "title": "Savory Tofu Scramble",
        "description": "Tofu scramble with peppers, spinach, and turmeric.",
        "ingredients": ["tofu", "bell pepper", "spinach", "turmeric", "olive oil"],
        "calories": 320,
        "prep_minutes": 12,
        "cost": 2.10,
        "macros": {"protein": 26, "carbs": 18, "fat": 16},
        "tags": ["vegan", "gluten_free"],
    },
    {
        "meal_type": "breakfast",
        "title": "Smoked Salmon Toast",
        "description": "Whole grain toast topped with smoked salmon and dill yogurt.",
        "ingredients": ["smoked salmon", "whole grain bread", "dill", "yogurt"],
        "calories": 340,
        "prep_minutes": 8,
        "cost": 3.60,
        "macros": {"protein": 25, "carbs": 32, "fat": 14},
        "tags": ["pescatarian", "mediterranean"],
    },
    {
        "meal_type": "breakfast",
        "title": "Steel-Cut Oats",
        "description": "Oats cooked with almond milk, topped with apple and walnuts.",
        "ingredients": ["steel-cut oats", "almond milk", "apple", "walnuts", "cinnamon"],
        "calories": 310,
        "prep_minutes": 20,
        "cost": 1.60,
        "macros": {"protein": 12, "carbs": 45, "fat": 9},
        "tags": ["vegan", "budget", "gluten_optional"],
    },
    {
        "meal_type": "breakfast",
        "title": "Veggie Egg Muffins",
        "description": "Baked eggs with broccoli, cheddar, and peppers.",
        "ingredients": ["eggs", "broccoli", "cheddar", "bell pepper"],
        "calories": 300,
        "prep_minutes": 25,
        "cost": 1.90,
        "macros": {"protein": 22, "carbs": 10, "fat": 18},
        "tags": ["vegetarian", "gluten_free"],
    },
    {
        "meal_type": "lunch",
        "title": "Quinoa Chickpea Bowl",
        "description": "Quinoa with roasted vegetables, chickpeas, and tahini drizzle.",
        "ingredients": ["quinoa", "chickpeas", "zucchini", "tahini", "lemon"],
        "calories": 540,
        "prep_minutes": 25,
        "cost": 3.20,
        "macros": {"protein": 22, "carbs": 68, "fat": 18},
        "tags": ["vegan", "gluten_free"],
    },
    {
        "meal_type": "lunch",
        "title": "Grilled Chicken Salad",
        "description": "Chicken breast over mixed greens with avocado and citrus vinaigrette.",
        "ingredients": ["chicken breast", "mixed greens", "avocado", "orange", "olive oil"],
        "calories": 520,
        "prep_minutes": 18,
        "cost": 4.10,
        "macros": {"protein": 42, "carbs": 24, "fat": 28},
        "tags": ["omnivore", "gluten_free"],
    },
    {
        "meal_type": "lunch",
        "title": "Lentil Soup with Greens",
        "description": "Herbed lentil soup with kale and tomatoes.",
        "ingredients": ["lentils", "kale", "tomato", "carrot", "vegetable broth"],
        "calories": 430,
        "prep_minutes": 35,
        "cost": 1.80,
        "macros": {"protein": 24, "carbs": 62, "fat": 8},
        "tags": ["vegan", "budget"],
    },
    {
        "meal_type": "lunch",
        "title": "Shrimp Grain Bowl",
        "description": "Brown rice with shrimp, edamame, and sesame-lime dressing.",
        "ingredients": ["shrimp", "brown rice", "edamame", "sesame oil", "lime"],
        "calories": 510,
        "prep_minutes": 22,
        "cost": 4.60,
        "macros": {"protein": 36, "carbs": 56, "fat": 16},
        "tags": ["pescatarian", "mediterranean"],
    },
    {
        "meal_type": "lunch",
        "title": "Turkey Hummus Wrap",
        "description": "Whole wheat wrap with roast turkey, hummus, and crunchy veggies.",
        "ingredients": ["turkey", "whole wheat wrap", "hummus", "spinach", "cucumber"],
        "calories": 480,
        "prep_minutes": 12,
        "cost": 3.00,
        "macros": {"protein": 34, "carbs": 44, "fat": 18},
        "tags": ["omnivore"],
    },
    {
        "meal_type": "dinner",
        "title": "Sheet Pan Salmon",
        "description": "Roasted salmon with sweet potatoes and green beans.",
        "ingredients": ["salmon", "sweet potato", "green beans", "olive oil"],
        "calories": 620,
        "prep_minutes": 28,
        "cost": 5.40,
        "macros": {"protein": 45, "carbs": 48, "fat": 28},
        "tags": ["pescatarian", "gluten_free"],
    },
    {
        "meal_type": "dinner",
        "title": "Chickpea Coconut Curry",
        "description": "Chickpeas simmered with coconut milk, spinach, and warm spices.",
        "ingredients": ["chickpeas", "coconut milk", "spinach", "garam masala", "rice"],
        "calories": 590,
        "prep_minutes": 30,
        "cost": 3.10,
        "macros": {"protein": 22, "carbs": 74, "fat": 22},
        "tags": ["vegan", "gluten_free"],
    },
    {
        "meal_type": "dinner",
        "title": "Lemon Herb Chicken",
        "description": "Grilled chicken thighs with quinoa pilaf and asparagus.",
        "ingredients": ["chicken thighs", "quinoa", "asparagus", "lemon", "parsley"],
        "calories": 610,
        "prep_minutes": 32,
        "cost": 4.20,
        "macros": {"protein": 46, "carbs": 56, "fat": 20},
        "tags": ["omnivore", "gluten_free"],
    },
    {
        "meal_type": "dinner",
        "title": "Black Bean Stuffed Peppers",
        "description": "Bell peppers baked with black beans, corn, and cauliflower rice.",
        "ingredients": ["black beans", "bell pepper", "corn", "cauliflower rice", "tomato"],
        "calories": 540,
        "prep_minutes": 35,
        "cost": 2.70,
        "macros": {"protein": 24, "carbs": 70, "fat": 14},
        "tags": ["vegan", "budget", "gluten_free"],
    },
    {
        "meal_type": "dinner",
        "title": "Seared Tofu Noodles",
        "description": "Seared tofu with soba noodles, bok choy, and ginger broth.",
        "ingredients": ["tofu", "soba noodles", "bok choy", "ginger", "tamari"],
        "calories": 560,
        "prep_minutes": 26,
        "cost": 3.50,
        "macros": {"protein": 32, "carbs": 68, "fat": 16},
        "tags": ["vegan"],
    },
    {
        "meal_type": "dinner",
        "title": "Garlic Shrimp Stir-Fry",
        "description": "Quick shrimp stir-fry with snap peas and ginger sauce.",
        "ingredients": ["shrimp", "snap peas", "ginger", "garlic", "sesame oil"],
        "calories": 520,
        "prep_minutes": 14,
        "cost": 4.00,
        "macros": {"protein": 38, "carbs": 36, "fat": 18},
        "tags": ["pescatarian", "gluten_free"],
    },
    {
        "meal_type": "dinner",
        "title": "Veggie Udon Stir-Fry",
        "description": "Udon noodles tossed with tofu, broccoli, and teriyaki glaze.",
        "ingredients": ["udon noodles", "tofu", "broccoli", "teriyaki sauce", "sesame seeds"],
        "calories": 540,
        "prep_minutes": 15,
        "cost": 2.90,
        "macros": {"protein": 26, "carbs": 72, "fat": 12},
        "tags": ["vegetarian"],
    },
]
