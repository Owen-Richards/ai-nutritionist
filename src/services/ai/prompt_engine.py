"""
Advanced Prompt Engineering System for AI Nutritionist
Optimized prompts for better performance, accuracy, and cost efficiency
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Structured prompt template with metadata"""
    name: str
    template: str
    variables: List[str]
    model_preference: str
    estimated_tokens: int
    cache_ttl_hours: int
    quality_score: float


class AdvancedPromptEngine:
    """Advanced prompt engineering with optimization and caching"""
    
    def __init__(self):
        self.templates = self._load_optimized_templates()
        self.prompt_analytics = {}
        
    def _load_optimized_templates(self) -> Dict[str, PromptTemplate]:
        """Load performance-optimized prompt templates"""
        
        return {
            "meal_planning_optimized": PromptTemplate(
                name="meal_planning_optimized",
                template="""You are a nutrition expert. Create a {meal_type} meal plan for {household_size} people.

CONSTRAINTS:
- Budget: ${budget}
- Dietary restrictions: {dietary_restrictions}
- Cuisine preferences: {cuisine_preferences}
- Cooking time: {max_cooking_time} minutes
- Nutritional goals: {nutrition_goals}

OUTPUT FORMAT (JSON):
{{
  "meals": [
    {{
      "name": "Meal Name",
      "ingredients": ["ingredient1", "ingredient2"],
      "cooking_time": 30,
      "estimated_cost": 12.50,
      "nutrition": {{"calories": 450, "protein": 25, "carbs": 45, "fat": 15}},
      "instructions": ["step1", "step2"]
    }}
  ],
  "total_cost": 45.00,
  "total_calories": 1800,
  "shopping_list": ["item1", "item2"]
}}

Provide only the JSON response.""",
                variables=["meal_type", "household_size", "budget", "dietary_restrictions", 
                          "cuisine_preferences", "max_cooking_time", "nutrition_goals"],
                model_preference="claude-3-haiku",
                estimated_tokens=800,
                cache_ttl_hours=12,
                quality_score=9.2
            ),
            
            "nutrition_analysis_fast": PromptTemplate(
                name="nutrition_analysis_fast",
                template="""Analyze this food item: "{food_item}"

Provide nutrition facts per 100g in this EXACT format:
CALORIES: [number]
PROTEIN: [number]g
CARBS: [number]g
FAT: [number]g
FIBER: [number]g
SUGAR: [number]g
SODIUM: [number]mg

HEALTH_RATING: [1-10]
KEY_BENEFITS: [2-3 benefits]
WARNINGS: [any concerns or none]""",
                variables=["food_item"],
                model_preference="titan-text-express",
                estimated_tokens=200,
                cache_ttl_hours=168,  # 7 days
                quality_score=8.5
            ),
            
            "recipe_suggestion_creative": PromptTemplate(
                name="recipe_suggestion_creative",
                template="""Create a creative recipe using these ingredients: {ingredients}

REQUIREMENTS:
- Cooking method: {cooking_method}
- Dietary style: {dietary_style}
- Difficulty: {difficulty_level}
- Prep time: Under {max_prep_time} minutes

Generate a recipe with:
1. Creative name
2. Ingredient list with quantities
3. Step-by-step instructions
4. Estimated nutrition per serving
5. Pro tips for best results

Make it engaging and practical.""",
                variables=["ingredients", "cooking_method", "dietary_style", 
                          "difficulty_level", "max_prep_time"],
                model_preference="claude-3-sonnet",
                estimated_tokens=600,
                cache_ttl_hours=24,
                quality_score=9.0
            ),
            
            "quick_nutrition_qa": PromptTemplate(
                name="quick_nutrition_qa",
                template="""Answer this nutrition question briefly and accurately: "{question}"

Context: User is {age} years old, {gender}, {activity_level} activity level, goal: {fitness_goal}

Provide:
1. Direct answer (2-3 sentences)
2. One practical tip
3. Any important warnings

Keep response under 150 words.""",
                variables=["question", "age", "gender", "activity_level", "fitness_goal"],
                model_preference="claude-3-haiku",
                estimated_tokens=150,
                cache_ttl_hours=72,
                quality_score=8.8
            ),
            
            "ingredient_substitution": PromptTemplate(
                name="ingredient_substitution",
                template="""Find substitutes for "{ingredient}" in this recipe context: {recipe_context}

Consider:
- Dietary restrictions: {restrictions}
- Available ingredients: {available_ingredients}
- Cooking method: {cooking_method}

Provide 3 best substitutes with:
- Substitute name
- Ratio (e.g., 1:1, 2:1)
- Impact on taste/texture
- Nutritional difference

Format as numbered list.""",
                variables=["ingredient", "recipe_context", "restrictions", 
                          "available_ingredients", "cooking_method"],
                model_preference="claude-3-haiku",
                estimated_tokens=250,
                cache_ttl_hours=48,
                quality_score=8.7
            )
        }
    
    def build_optimized_prompt(self, template_name: str, variables: Dict[str, Any], 
                             context: Optional[Dict[str, Any]] = None) -> Tuple[str, PromptTemplate]:
        """
        Build optimized prompt with context awareness and caching
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        # Validate required variables
        missing_vars = set(template.variables) - set(variables.keys())
        if missing_vars:
            raise ValueError(f"Missing variables: {missing_vars}")
        
        # Add context-aware enhancements
        enhanced_variables = self._enhance_variables_with_context(variables, context)
        
        # Build prompt
        try:
            prompt = template.template.format(**enhanced_variables)
        except KeyError as e:
            raise ValueError(f"Error formatting template: {e}")
        
        # Track prompt usage for analytics
        self._track_prompt_usage(template_name, len(prompt))
        
        return prompt, template
    
    def _enhance_variables_with_context(self, variables: Dict[str, Any], 
                                      context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enhance variables with context-aware information
        """
        enhanced = variables.copy()
        
        if not context:
            return enhanced
        
        # Add time-based context
        current_time = datetime.now()
        if 'meal_type' in enhanced:
            if current_time.hour < 10:
                enhanced['time_context'] = "It's morning time"
            elif current_time.hour < 15:
                enhanced['time_context'] = "It's lunch time"
            else:
                enhanced['time_context'] = "It's evening time"
        
        # Add user preferences from context
        if 'user_profile' in context:
            profile = context['user_profile']
            enhanced['dietary_restrictions'] = enhanced.get(
                'dietary_restrictions', 
                profile.get('dietary_restrictions', 'none')
            )
            enhanced['cuisine_preferences'] = enhanced.get(
                'cuisine_preferences',
                profile.get('cuisine_preferences', 'any')
            )
        
        # Add seasonal context
        month = current_time.month
        if month in [12, 1, 2]:
            enhanced['seasonal_note'] = "Consider warming, hearty options for winter"
        elif month in [6, 7, 8]:
            enhanced['seasonal_note'] = "Consider light, refreshing options for summer"
        
        return enhanced
    
    def generate_cache_key(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Generate intelligent cache key for prompt responses
        """
        # Create a normalized representation of the prompt
        cache_data = {
            'template': template_name,
            'variables': {k: str(v) for k, v in sorted(variables.items())}
        }
        
        # Add time-based cache variation for time-sensitive prompts
        if template_name in ['meal_planning_optimized']:
            # Cache by week for meal plans
            cache_data['time_bucket'] = datetime.now().strftime('%Y-W%U')
        elif template_name in ['nutrition_analysis_fast']:
            # Long-term cache for nutrition facts
            pass  # No time component needed
        else:
            # Daily cache for other prompts
            cache_data['time_bucket'] = datetime.now().strftime('%Y-%m-%d')
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"prompt_{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    def _track_prompt_usage(self, template_name: str, prompt_length: int) -> None:
        """
        Track prompt usage for analytics and optimization
        """
        if template_name not in self.prompt_analytics:
            self.prompt_analytics[template_name] = {
                'usage_count': 0,
                'total_tokens': 0,
                'avg_tokens': 0,
                'last_used': None
            }
        
        analytics = self.prompt_analytics[template_name]
        analytics['usage_count'] += 1
        analytics['total_tokens'] += prompt_length
        analytics['avg_tokens'] = analytics['total_tokens'] / analytics['usage_count']
        analytics['last_used'] = datetime.now().isoformat()
    
    def get_prompt_analytics(self) -> Dict[str, Any]:
        """
        Get prompt usage analytics for optimization
        """
        return {
            'templates': self.prompt_analytics,
            'total_prompts': sum(a['usage_count'] for a in self.prompt_analytics.values()),
            'most_used': max(self.prompt_analytics.items(), 
                           key=lambda x: x[1]['usage_count'], 
                           default=('none', {'usage_count': 0})),
            'optimization_opportunities': self._identify_optimization_opportunities()
        }
    
    def _identify_optimization_opportunities(self) -> List[str]:
        """
        Identify opportunities for prompt optimization
        """
        opportunities = []
        
        for template_name, analytics in self.prompt_analytics.items():
            template = self.templates[template_name]
            
            # Check for high token usage
            if analytics['avg_tokens'] > template.estimated_tokens * 1.2:
                opportunities.append(
                    f"Template '{template_name}' uses {analytics['avg_tokens']:.0f} tokens on average, "
                    f"consider optimizing (estimated: {template.estimated_tokens})"
                )
            
            # Check for frequently used templates
            if analytics['usage_count'] > 100 and template.cache_ttl_hours < 24:
                opportunities.append(
                    f"Template '{template_name}' is heavily used ({analytics['usage_count']} times), "
                    f"consider extending cache TTL from {template.cache_ttl_hours}h"
                )
        
        return opportunities
    
    def optimize_prompt_for_model(self, prompt: str, model_id: str) -> str:
        """
        Optimize prompt based on specific model characteristics
        """
        if 'claude' in model_id.lower():
            # Claude models prefer structured XML-like tags
            if '<thinking>' not in prompt and 'analyze' in prompt.lower():
                prompt = f"<thinking>\nI need to analyze this request carefully.\n</thinking>\n\n{prompt}"
        
        elif 'titan' in model_id.lower():
            # Titan models work better with clear instruction format
            if not prompt.startswith('Instructions:'):
                prompt = f"Instructions: {prompt}\n\nPlease follow the instructions exactly."
        
        elif 'llama' in model_id.lower():
            # Llama models prefer conversational format
            if not prompt.startswith('[INST]'):
                prompt = f"[INST] {prompt} [/INST]"
        
        return prompt


# Global instance
prompt_engine = AdvancedPromptEngine()
