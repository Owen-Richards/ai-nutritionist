"""
Smart caching with template-based personalization
Cache TEMPLATES, not responses - personalize with user data
This gives both cost savings AND personalization
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SmartResponseCache:
    """
    Cache system that uses templates for personalization

    NEW Strategy (addressing investor feedback):
    1. Cache TEMPLATES with placeholders (not full responses)
    2. Personalize templates with user-specific data
    3. Only hit AI for truly unique queries
    4. Result: Personalized responses at cached cost

    This solves: "90% cache hit = 90% generic responses"
    Now: 90% cache hit = 90% personalized-from-template responses
    """

    def __init__(self, cache_ttl_hours: int = 24):
        """
        Initialize cache system

        Args:
            cache_ttl_hours: Cache validity period in hours
        """
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # Different cache strategies
        self.exact_cache: Dict[str, Dict] = {}  # Exact query matches
        self.semantic_cache: Dict[str, Dict] = {}  # Similar queries
        self.pattern_cache: Dict[str, Dict] = {}  # Common patterns
        self.user_cache: Dict[str, Dict] = {}  # Per-user preferences

        # Pre-computed responses for common queries
        self.static_responses = self._load_static_responses()

        # Track cache performance
        self.stats = {
            "total_requests": 0,
            "static_hits": 0,
            "exact_hits": 0,
            "semantic_hits": 0,
            "pattern_hits": 0,
            "ai_calls": 0,
            "cost_saved": 0.0,
        }

    def _load_static_responses(self) -> Dict:
        """Pre-computed responses for common queries (zero marginal cost)"""
        return {
            "healthy_breakfast": {
                "pattern": ["breakfast", "healthy", "morning"],
                "response": (
                    "Here are 3 healthy breakfast options:\n\n"
                    "🥣 **Overnight Oats**: Mix 1/2 cup oats with Greek yogurt, "
                    "chia seeds, and berries. Prep the night before. (~300 cal, $1.20)\n\n"
                    "🥑 **Avocado Toast**: Whole grain bread with mashed avocado, "
                    "poached egg, and tomatoes. (~350 cal, $2.50)\n\n"
                    "🍳 **Veggie Scramble**: 2 eggs with spinach, peppers, and mushrooms. "
                    "Add whole grain toast. (~320 cal, $1.80)\n\n"
                    "💡 Tip: Prep ingredients Sunday for faster weekday mornings!"
                ),
            },
            "lose_weight": {
                "pattern": ["lose", "weight", "diet", "slim"],
                "response": (
                    "For healthy, sustainable weight loss:\n\n"
                    "📊 **Create a 500-calorie daily deficit**\n"
                    "   • Track your food for 3 days to understand baseline\n"
                    "   • Use smaller plates (9-inch vs 12-inch)\n\n"
                    "🥗 **Focus on whole foods**\n"
                    "   • Fill half your plate with vegetables\n"
                    "   • Choose lean proteins (chicken, fish, legumes)\n"
                    "   • Swap refined carbs for whole grains\n\n"
                    "💧 **Drink 8 glasses of water daily**\n"
                    "   • Start each meal with water\n"
                    "   • Often thirst disguises as hunger\n\n"
                    "🚶 **Add 30 minutes of daily walking**\n"
                    "   • Start with 10 minutes if needed\n"
                    "   • Gradually increase duration\n\n"
                    "🎯 Realistic goal: 1-2 lbs per week"
                ),
            },
            "meal_prep": {
                "pattern": ["meal", "prep", "sunday", "batch"],
                "response": (
                    "Sunday Meal Prep Guide (saves 5+ hours weekly):\n\n"
                    "**1. PROTEINS** (90 min)\n"
                    "   • Grill 3 lbs chicken breast\n"
                    "   • Bake 2 lbs salmon\n"
                    "   • Hard boil 12 eggs\n\n"
                    "**2. CARBS** (45 min)\n"
                    "   • Cook 3 cups quinoa\n"
                    "   • Roast sweet potatoes\n"
                    "   • Prep overnight oats\n\n"
                    "**3. VEGGIES** (30 min)\n"
                    "   • Roast mixed vegetables (400°F, 25 min)\n"
                    "   • Wash and chop salad greens\n"
                    "   • Steam broccoli and green beans\n\n"
                    "**4. PORTIONS** (20 min)\n"
                    "   • Divide into 5 containers\n"
                    "   • Label with day and calories\n"
                    "   • Store in fridge (4-5 days safe)\n\n"
                    "💰 Cost: ~$45 for 5 days of meals (vs $75+ buying daily)"
                ),
            },
            "protein_sources": {
                "pattern": ["protein", "sources", "vegetarian", "vegan"],
                "response": (
                    "Great protein sources (cost per 20g protein):\n\n"
                    "**LEGUMES**\n"
                    "🥜 Lentils: 18g per cup ($0.30)\n"
                    "🥜 Chickpeas: 15g per cup ($0.35)\n"
                    "🥜 Black beans: 15g per cup ($0.25)\n\n"
                    "**DAIRY**\n"
                    "🥛 Greek yogurt: 20g per cup ($0.80)\n"
                    "🧀 Cottage cheese: 25g per cup ($0.90)\n"
                    "🥛 Regular milk: 8g per cup ($0.25)\n\n"
                    "**GRAINS**\n"
                    "🌾 Quinoa: 8g per cup ($0.60)\n"
                    "🌾 Oats: 6g per cup ($0.20)\n"
                    "🍞 Whole wheat bread: 4g per slice ($0.15)\n\n"
                    "**NUTS & SEEDS**\n"
                    "🥜 Almonds: 6g per ounce ($0.50)\n"
                    "🥜 Peanut butter: 8g per 2 tbsp ($0.30)\n"
                    "🌰 Chia seeds: 5g per 2 tbsp ($0.40)\n\n"
                    "💡 Tip: Combine legumes + grains for complete protein!"
                ),
            },
            "quick_dinner": {
                "pattern": ["quick", "dinner", "easy", "fast", "30 minutes"],
                "response": (
                    "Quick 30-Minute Dinners:\n\n"
                    "🍳 **One-Pan Chicken & Veggies** (25 min, $3.50/serving)\n"
                    "   • Season chicken breast\n"
                    "   • Toss with broccoli, peppers, olive oil\n"
                    "   • Bake 400°F for 20 minutes\n\n"
                    "🍝 **Pasta Primavera** (20 min, $2.20/serving)\n"
                    "   • Boil whole grain pasta\n"
                    "   • Sauté mixed vegetables\n"
                    "   • Toss with olive oil and parmesan\n\n"
                    "🌮 **Fish Tacos** (15 min, $4.00/serving)\n"
                    "   • Pan-sear white fish\n"
                    "   • Warm corn tortillas\n"
                    "   • Top with cabbage slaw and lime\n\n"
                    "💡 Keep frozen vegetables on hand for faster prep!"
                ),
            },
            "save_money": {
                "pattern": ["save", "money", "budget", "cheap", "affordable"],
                "response": (
                    "Save $150+/month on groceries:\n\n"
                    "💰 **Buy in Bulk**\n"
                    "   • Rice, oats, beans save 40%\n"
                    "   • Costco family packs save $$$\n\n"
                    "❄️ **Use Frozen Produce**\n"
                    "   • Same nutrition, 50% cheaper\n"
                    "   • No waste from spoilage\n\n"
                    "🏪 **Store Brands**\n"
                    "   • Usually identical quality\n"
                    "   • Save 20-30% instantly\n\n"
                    "📅 **Meal Plan Weekly**\n"
                    "   • Shop with a list (no impulse buys)\n"
                    "   • Use what you have first\n\n"
                    "🍗 **Batch Cook Proteins**\n"
                    "   • Chicken thighs cheaper than breasts\n"
                    "   • Whole chicken = $1.50/lb vs $4/lb breasts\n\n"
                    "📊 Average savings: $191/month"
                ),
            },
        }

    async def get_or_generate(
        self,
        query: str,
        user_id: str,
        use_ai_callback: Optional[Callable[[str, str], Awaitable[str]]] = None,
    ) -> Dict:
        """
        Try to serve from cache, only use AI if absolutely necessary

        Args:
            query: User's query
            user_id: User identifier
            use_ai_callback: Optional async function to call AI if needed

        Returns:
            Response dictionary with content, source, and cost
        """
        self.stats["total_requests"] += 1

        # 1. Check static responses first (zero cost)
        static_response = self._check_static_patterns(query)
        if static_response:
            self.stats["static_hits"] += 1
            self.stats["cost_saved"] += 0.015
            logger.info(f"Static cache hit for query: {query[:50]}")
            return {
                "response": static_response,
                "source": "static_cache",
                "cost": 0.0,
                "cached": True,
            }

        # 2. Check exact cache
        cache_key = self._generate_cache_key(query, user_id)
        if cache_key in self.exact_cache:
            cached = self.exact_cache[cache_key]
            if self._is_cache_valid(cached):
                self.stats["exact_hits"] += 1
                self.stats["cost_saved"] += 0.015
                logger.info(f"Exact cache hit for query: {query[:50]}")
                return {
                    "response": cached["response"],
                    "source": "exact_cache",
                    "cost": 0.0,
                    "cached": True,
                }

        # 3. Check semantic similarity cache
        similar_response = self._find_similar_cached(query)
        if similar_response:
            self.stats["semantic_hits"] += 1
            self.stats["cost_saved"] += 0.015
            logger.info(f"Semantic cache hit for query: {query[:50]}")
            return {
                "response": similar_response,
                "source": "semantic_cache",
                "cost": 0.0,
                "cached": True,
            }

        # 4. Check user patterns
        user_pattern_response = self._check_user_patterns(user_id, query)
        if user_pattern_response:
            self.stats["pattern_hits"] += 1
            self.stats["cost_saved"] += 0.015
            logger.info(f"User pattern cache hit for: {query[:50]}")
            return {
                "response": user_pattern_response,
                "source": "user_pattern_cache",
                "cost": 0.0,
                "cached": True,
            }

        # 5. Last resort - use AI (only for premium users)
        if use_ai_callback:
            self.stats["ai_calls"] += 1
            logger.info(f"AI call required for query: {query[:50]}")

            ai_response = await use_ai_callback(query, user_id)

            # Cache the response for future use
            self._cache_response(query, user_id, ai_response)

            return {
                "response": ai_response,
                "source": "ai_generated",
                "cost": 0.015,  # Approximate Bedrock cost
                "cached": False,
            }

        # 6. Fallback for free users who hit limit
        logger.info(f"Fallback response for query: {query[:50]}")
        return {
            "response": self._generate_fallback_response(query),
            "source": "fallback",
            "cost": 0.0,
            "cached": False,
        }

    def _check_static_patterns(self, query: str) -> Optional[str]:
        """Check if query matches static patterns"""
        query_lower = query.lower()

        for key, data in self.static_responses.items():
            # Check if ALL pattern words are in the query
            if all(word in query_lower for word in data["pattern"]):
                return data["response"]

        return None

    def _generate_cache_key(self, query: str, user_id: str) -> str:
        """Generate unique cache key"""
        # Normalize query for better cache hits
        normalized = query.lower().strip()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        combined = f"{user_id}:{normalized}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _is_cache_valid(self, cached_item: Dict) -> bool:
        """Check if cached item is still valid"""
        if "timestamp" not in cached_item:
            return False

        age = datetime.now() - cached_item["timestamp"]
        return age < self.cache_ttl

    def _find_similar_cached(self, query: str) -> Optional[str]:
        """
        Find semantically similar cached responses
        Uses Jaccard similarity for simplicity
        """
        query_words = set(query.lower().split())
        best_match = None
        best_similarity = 0.0

        for cached_query, cached_data in self.semantic_cache.items():
            cached_words = set(cached_query.lower().split())

            # Jaccard similarity
            intersection = len(query_words & cached_words)
            union = len(query_words | cached_words)

            if union == 0:
                continue

            similarity = intersection / union

            if similarity > 0.7 and similarity > best_similarity:
                best_similarity = similarity
                best_match = cached_data.get("response")

        return best_match

    def _check_user_patterns(self, user_id: str, query: str) -> Optional[str]:
        """Check user's historical patterns"""
        user_patterns = self.user_cache.get(user_id, {})

        # If user frequently asks similar questions, serve cached response
        query_lower = query.lower()
        for pattern, response in user_patterns.items():
            if pattern in query_lower:
                return response

        return None

    def _cache_response(self, query: str, user_id: str, response: str):
        """Cache response for future use"""
        cache_key = self._generate_cache_key(query, user_id)

        timestamp = datetime.now()

        # Add to exact cache
        self.exact_cache[cache_key] = {"response": response, "timestamp": timestamp}

        # Also add to semantic cache (normalized query)
        normalized_query = query.lower().strip()
        self.semantic_cache[normalized_query] = {"response": response, "timestamp": timestamp}

        # Track user patterns
        if user_id not in self.user_cache:
            self.user_cache[user_id] = {}

        # Store simplified pattern (key words only)
        key_words = [w for w in query.lower().split() if len(w) > 4][:3]
        if key_words:
            pattern_key = " ".join(key_words)
            self.user_cache[user_id][pattern_key] = response

        logger.debug(f"Cached response for query: {query[:50]}")

    def _generate_fallback_response(self, query: str) -> str:
        """Generate helpful fallback for free users who hit limit"""
        return (
            "I'd love to provide a personalized AI response! 🤖\n\n"
            "As a free user, you have access to:\n"
            "✅ Our recipe database (1000+ recipes)\n"
            "✅ Basic nutrition tips\n"
            "✅ Meal prep guides\n\n"
            "For AI-powered personalized nutrition coaching, consider upgrading to Premium ($9.99/mo):\n"
            "• Unlimited AI interactions\n"
            "• Smart grocery lists that save $$\n"
            "• Family meal planning\n"
            "• Priority support\n\n"
            "Reply UPGRADE to subscribe or check out /free-resources for helpful guides!"
        )

    def get_cache_stats(self) -> Dict:
        """Get cache performance stats"""
        total_cached = len(self.exact_cache) + len(self.semantic_cache) + len(self.static_responses)

        cache_hit_rate = 0.0
        if self.stats["total_requests"] > 0:
            hits = (
                self.stats["static_hits"]
                + self.stats["exact_hits"]
                + self.stats["semantic_hits"]
                + self.stats["pattern_hits"]
            )
            cache_hit_rate = (hits / self.stats["total_requests"]) * 100

        return {
            "total_cached_responses": total_cached,
            "exact_cache_size": len(self.exact_cache),
            "semantic_cache_size": len(self.semantic_cache),
            "static_responses": len(self.static_responses),
            "users_with_patterns": len(self.user_cache),
            "total_requests": self.stats["total_requests"],
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "ai_calls": self.stats["ai_calls"],
            "estimated_cost_saved": f"${self.stats['cost_saved']:.2f}",
            "breakdown": {
                "static_hits": self.stats["static_hits"],
                "exact_hits": self.stats["exact_hits"],
                "semantic_hits": self.stats["semantic_hits"],
                "pattern_hits": self.stats["pattern_hits"],
            },
        }

    def clear_expired_cache(self):
        """Remove expired items from cache"""
        now = datetime.now()

        # Clear exact cache
        expired_keys = [
            key
            for key, item in self.exact_cache.items()
            if "timestamp" in item and (now - item["timestamp"]) > self.cache_ttl
        ]
        for key in expired_keys:
            del self.exact_cache[key]

        # Clear semantic cache
        expired_queries = [
            query
            for query, item in self.semantic_cache.items()
            if "timestamp" in item and (now - item["timestamp"]) > self.cache_ttl
        ]
        for query in expired_queries:
            del self.semantic_cache[query]

        logger.info(f"Cleared {len(expired_keys) + len(expired_queries)} expired cache entries")

    def get_personalized_with_cache(self, query: str, user_profile: Dict) -> Dict:
        """
        NEW: Get personalized response using cached templates

        This addresses the investor concern about generic cached responses
        We cache the STRUCTURE, personalize with user data

        Args:
            query: User's query
            user_profile: Dict with user data (name, dietary_restrictions, goals, etc.)

        Returns:
            Personalized response dict
        """
        # Try to find a matching template
        template = self._get_cached_template(query)

        if template:
            # Personalize the template with user data
            personalized_response = self._personalize_template(template, user_profile)

            logger.info(f"Template cache hit with personalization for: {query[:50]}")

            return {
                "response": personalized_response,
                "source": "personalized_template",
                "cost": 0.0,  # Zero cost
                "cached": True,
                "personalized": True,
            }

        # No template found - would need AI for this one
        return {
            "response": None,
            "source": "needs_ai",
            "cost": 0.015,
            "cached": False,
            "personalized": False,
            "message": "This query requires AI personalization",
        }

    def _get_cached_template(self, query: str) -> Optional[Dict]:
        """
        Get response template for query type

        Templates contain placeholders like {user_name}, {dietary_restrictions}, etc.
        """
        query_lower = query.lower()

        # Define templates for common query types
        templates = {
            "breakfast_ideas": {
                "patterns": ["breakfast", "morning meal", "what should i eat for breakfast"],
                "template": (
                    "Good morning{user_name_greeting}! Here are 3 healthy breakfast options "
                    "that fit your {dietary_label}diet:\n\n"
                    "🥣 **Overnight Oats**: Mix 1/2 cup oats with Greek yogurt, "
                    "chia seeds, and {preferred_fruit}. Prep the night before. (~300 cal, $1.20)\n\n"
                    "🥑 **Avocado Toast**: Whole grain bread with mashed avocado, "
                    "poached egg{egg_restriction}, and tomatoes. (~350 cal, $2.50)\n\n"
                    "🍳 **Veggie Scramble**: 2 eggs{egg_restriction} with spinach, peppers, and mushrooms. "
                    "Add whole grain toast. (~320 cal, $1.80)\n\n"
                    "💡 Tip: Prep ingredients Sunday for faster weekday mornings!\n"
                    "{goal_message}"
                ),
                "variables": [
                    "user_name_greeting",
                    "dietary_label",
                    "preferred_fruit",
                    "egg_restriction",
                    "goal_message",
                ],
            },
            "weight_loss": {
                "patterns": ["lose weight", "weight loss", "get slim", "shed pounds"],
                "template": (
                    "Hi{user_name_greeting}! For healthy, sustainable weight loss{goal_context}:\n\n"
                    "📊 **Create a 500-calorie daily deficit**\n"
                    "   • Your target: ~{calorie_target} calories/day\n"
                    "   • Track your food for 3 days to understand baseline\n"
                    "   • Use smaller plates (9-inch vs 12-inch)\n\n"
                    "🥗 **Focus on whole foods**{dietary_note}\n"
                    "   • Fill half your plate with vegetables\n"
                    "   • Choose lean proteins (chicken, fish{protein_options})\n"
                    "   • Swap refined carbs for whole grains\n\n"
                    "💧 **Drink 8 glasses of water daily**\n"
                    "   • Start each meal with water\n"
                    "   • Often thirst disguises as hunger\n\n"
                    "🚶 **Add 30 minutes of daily walking**\n"
                    "   • Start with 10 minutes if needed\n"
                    "   • Gradually increase duration\n\n"
                    "🎯 Realistic goal: 1-2 lbs per week = {weeks_to_goal} weeks to your {target_weight}lb goal"
                ),
                "variables": [
                    "user_name_greeting",
                    "goal_context",
                    "calorie_target",
                    "dietary_note",
                    "protein_options",
                    "weeks_to_goal",
                    "target_weight",
                ],
            },
            "meal_prep": {
                "patterns": ["meal prep", "sunday prep", "batch cooking", "prep meals"],
                "template": (
                    "Great question{user_name_greeting}! Here's your personalized Sunday meal prep guide{dietary_label}:\n\n"
                    "**1. PROTEINS** (90 min)\n"
                    "   • {protein_option_1}\n"
                    "   • {protein_option_2}\n"
                    "   • {protein_option_3}\n\n"
                    "**2. CARBS** (45 min)\n"
                    "   • {carb_option_1}\n"
                    "   • {carb_option_2}\n"
                    "   • Prep overnight oats\n\n"
                    "**3. VEGGIES** (30 min)\n"
                    "   • Roast {favorite_vegetables} (400°F, 25 min)\n"
                    "   • Wash and chop salad greens\n"
                    "   • Steam broccoli and green beans\n\n"
                    "**4. PORTIONS** (20 min)\n"
                    "   • Divide into {num_servings} containers (for {household_size} people)\n"
                    "   • Label with day and calories (~{calories_per_meal} each)\n"
                    "   • Store in fridge (4-5 days safe)\n\n"
                    "💰 Cost: ~${estimated_cost} for {num_days} days of meals (vs ${dining_out_cost}+ buying daily)\n"
                    "{savings_message}"
                ),
                "variables": [
                    "user_name_greeting",
                    "dietary_label",
                    "protein_option_1",
                    "protein_option_2",
                    "protein_option_3",
                    "carb_option_1",
                    "carb_option_2",
                    "favorite_vegetables",
                    "num_servings",
                    "household_size",
                    "calories_per_meal",
                    "estimated_cost",
                    "num_days",
                    "dining_out_cost",
                    "savings_message",
                ],
            },
        }

        # Find matching template
        for template_name, template_data in templates.items():
            if any(pattern in query_lower for pattern in template_data["patterns"]):
                return template_data

        return None

    def _personalize_template(self, template: Dict, user_profile: Dict) -> str:
        """
        Personalize template with user data

        This is the magic: cached template + user data = personalized response at zero cost
        """
        template_text = template["template"]

        # Extract user profile data with defaults
        user_name = user_profile.get("name", "")
        dietary_restrictions = user_profile.get("dietary_restrictions", [])
        goals = user_profile.get("goals", [])
        weight_goal = user_profile.get("weight_goal")
        current_weight = user_profile.get("current_weight")
        household_size = user_profile.get("household_size", 2)
        preferences = user_profile.get("food_preferences", {})

        # Build personalization variables
        variables = {
            "user_name_greeting": f", {user_name}" if user_name else "",
            "dietary_label": self._get_dietary_label(dietary_restrictions),
            "dietary_note": self._get_dietary_note(dietary_restrictions),
            "preferred_fruit": preferences.get("fruit", "berries"),
            "favorite_vegetables": preferences.get("vegetables", "mixed vegetables"),
            "egg_restriction": " (or tofu scramble)" if "vegan" in dietary_restrictions else "",
            "goal_message": self._get_goal_message(goals),
            "goal_context": self._get_goal_context(goals, weight_goal, current_weight),
            "calorie_target": self._calculate_calorie_target(current_weight, weight_goal),
            "protein_options": self._get_protein_options(dietary_restrictions),
            "weeks_to_goal": (
                self._calculate_weeks_to_goal(current_weight, weight_goal)
                if current_weight and weight_goal
                else "12-16"
            ),
            "target_weight": weight_goal if weight_goal else "target",
            "protein_option_1": self._get_protein_prep(dietary_restrictions, 1),
            "protein_option_2": self._get_protein_prep(dietary_restrictions, 2),
            "protein_option_3": self._get_protein_prep(dietary_restrictions, 3),
            "carb_option_1": "Cook 3 cups quinoa",
            "carb_option_2": "Roast sweet potatoes",
            "num_servings": household_size * 5,  # 5 days of meals
            "household_size": household_size,
            "calories_per_meal": (
                self._calculate_calorie_target(current_weight, weight_goal) // 3
                if current_weight
                else 500
            ),
            "estimated_cost": self._estimate_meal_prep_cost(household_size),
            "num_days": 5,
            "dining_out_cost": 15 * household_size * 5,  # $15/person/meal * 5 days
            "savings_message": f"That's a savings of ${15 * household_size * 5 - self._estimate_meal_prep_cost(household_size):.0f} this week!",
        }

        # Replace all variables in template
        personalized = template_text
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            personalized = personalized.replace(placeholder, str(var_value))

        return personalized

    def _get_dietary_label(self, restrictions: List[str]) -> str:
        """Get dietary restriction label"""
        if not restrictions:
            return ""
        if "vegan" in restrictions:
            return "vegan "
        if "vegetarian" in restrictions:
            return "vegetarian "
        if "gluten-free" in restrictions:
            return "gluten-free "
        return ""

    def _get_dietary_note(self, restrictions: List[str]) -> str:
        """Get personalized dietary note"""
        if "vegan" in restrictions:
            return " (all plant-based)"
        if "vegetarian" in restrictions:
            return " (no meat)"
        return ""

    def _get_goal_message(self, goals: List[str]) -> str:
        """Get goal-specific message"""
        if not goals:
            return ""
        goal = goals[0] if goals else ""
        messages = {
            "lose_weight": "Focus on protein and fiber to stay full longer!",
            "gain_muscle": "Aim for 0.8-1g protein per lb of body weight!",
            "maintain": "Consistency is key - meal prep helps!",
            "save_money": "These options save you $65/month vs dining out!",
        }
        return messages.get(goal, "")

    def _get_goal_context(
        self, goals: List[str], weight_goal: Optional[float], current_weight: Optional[float]
    ) -> str:
        """Get context about user's goal"""
        if not goals or not weight_goal or not current_weight:
            return ""
        pounds_to_lose = current_weight - weight_goal
        return f" to reach your goal of losing {pounds_to_lose:.0f} lbs"

    def _calculate_calorie_target(
        self, current_weight: Optional[float], weight_goal: Optional[float]
    ) -> int:
        """Calculate daily calorie target"""
        if not current_weight:
            return 1800  # Default

        # Rough estimate: current_weight * 12-14 for maintenance, -500 for loss
        maintenance = int(current_weight * 13)

        if weight_goal and weight_goal < current_weight:
            return maintenance - 500

        return maintenance

    def _calculate_weeks_to_goal(self, current_weight: float, weight_goal: float) -> int:
        """Calculate weeks to reach goal at 1.5 lbs/week"""
        pounds_to_lose = abs(current_weight - weight_goal)
        return int(pounds_to_lose / 1.5)

    def _get_protein_options(self, restrictions: List[str]) -> str:
        """Get protein options based on restrictions"""
        if "vegan" in restrictions:
            return ", legumes, tofu, tempeh"
        if "vegetarian" in restrictions:
            return ", legumes, eggs, dairy"
        return ", legumes"

    def _get_protein_prep(self, restrictions: List[str], option_num: int) -> str:
        """Get protein prep instruction based on restrictions"""
        if "vegan" in restrictions:
            options = [
                "Marinate and bake 2 blocks of tofu",
                "Cook 3 cups of lentils",
                "Prepare chickpea salad",
            ]
        elif "vegetarian" in restrictions:
            options = [
                "Hard boil 12 eggs",
                "Cook 3 cups of lentils",
                "Prepare Greek yogurt parfaits",
            ]
        else:
            options = [
                "Grill 3 lbs chicken breast",
                "Bake 2 lbs salmon",
                "Hard boil 12 eggs",
            ]

        return options[option_num - 1] if option_num <= len(options) else options[0]

    def _estimate_meal_prep_cost(self, household_size: int) -> int:
        """Estimate meal prep cost"""
        cost_per_person_per_day = 9  # $9/person/day for healthy meals
        return cost_per_person_per_day * household_size * 5  # 5 days
