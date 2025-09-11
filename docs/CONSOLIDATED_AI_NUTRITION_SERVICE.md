# Consolidated AI & Nutrition Service

## Overview

The `ConsolidatedAINutritionService` is a comprehensive service that unifies all AI-powered nutrition functionality in the AI Nutritionist application. This consolidation improves maintainability, reduces code duplication, and provides a single point of integration for all nutrition-related AI features.

## Features Consolidated

### 1. AI-Powered Meal Planning
- **Source Services**: `ai_service.py`, `adaptive_meal_planning_service.py`
- **Capabilities**: 
  - AWS Bedrock integration for intelligent meal plan generation
  - User profile-based meal customization
  - Nutrition strategy suggestions (intermittent fasting, gut health, plant-forward)
  - Cost-optimized caching system
  - Enhanced recipe enrichment

### 2. Nutrition Analysis
- **Source Services**: `edamam_service.py`, `nutrition_tracking_service.py`
- **Capabilities**:
  - Comprehensive nutrition analysis using Edamam API
  - Daily nutrition tracking with wellness metrics
  - Trend analysis and insights
  - Vitamin and mineral assessment
  - Daily value percentage calculations

### 3. User Profiling & Adaptation
- **Source Services**: `seamless_profiling_service.py`
- **Capabilities**:
  - Progressive user profile learning
  - Dietary restriction and allergy management
  - Cooking skill and time preference adaptation
  - Health condition consideration
  - Budget-conscious meal planning

### 4. Recipe Enhancement
- **Capabilities**:
  - Multi-criteria recipe search
  - User preference scoring
  - Ingredient substitution suggestions
  - Difficulty level calculation
  - WhatsApp-optimized formatting

## Architecture

```
ConsolidatedAINutritionService
├── AI Meal Planning
│   ├── generate_meal_plan()
│   ├── _build_meal_plan_prompt()
│   ├── _suggest_nutrition_strategy()
│   └── _enrich_with_enhanced_recipes()
├── Nutrition Analysis
│   ├── analyze_meal_nutrition()
│   ├── get_enhanced_nutrition_analysis()
│   └── _process_nutrition_data()
├── Recipe Search & Enhancement
│   ├── enhanced_recipe_search()
│   ├── suggest_substitutions()
│   └── format_recipe_for_whatsapp()
├── Nutrition Tracking
│   ├── track_daily_nutrition()
│   ├── get_nutrition_history()
│   └── _analyze_nutrition_trends()
└── Utility Methods
    ├── Caching system
    ├── AWS Bedrock integration
    └── Data formatting
```

## Data Models

### UserProfile
```python
@dataclass
class UserProfile:
    user_id: str
    dietary_restrictions: List[str] = None
    allergies: List[str] = None
    household_size: int = 2
    weekly_budget: float = 75.0
    fitness_goals: str = 'maintenance'
    daily_calories: int = 2000
    health_conditions: List[str] = None
    cooking_skill: str = 'intermediate'
    meal_preferences: Dict[str, Any] = None
    nutrition_goals: Dict[str, float] = None
```

### DayNutrition
```python
@dataclass
class DayNutrition:
    date: str
    kcal: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    sodium: float = 0
    sugar_added: float = 0
    water_cups: float = 0
    steps: Optional[int] = None
    mood: Optional[str] = None
    energy: Optional[str] = None
    digestion: Optional[str] = None
    sleep_quality: Optional[str] = None
    meals_ate: List[str] = None
    meals_skipped: List[str] = None
    meals_modified: List[str] = None
    snacks: List[str] = None
```

## Key Methods

### Meal Planning
```python
def generate_meal_plan(self, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]
```
Generates a comprehensive weekly meal plan using AI, with user-specific optimization and recipe enrichment.

### Nutrition Analysis
```python
async def analyze_meal_nutrition(self, ingredients_list: List[str], user_id: str = None) -> Dict
```
Analyzes nutritional content of meals using Edamam API with intelligent caching.

### Enhanced Recipe Search
```python
async def enhanced_recipe_search(self, query: str, user_profile: Dict[str, Any], limit: int = 5) -> Dict[str, Any]
```
Searches for recipes with user preference optimization and scoring.

### Nutrition Tracking
```python
def track_daily_nutrition(self, user_id: str, nutrition_data: DayNutrition) -> Dict[str, Any]
```
Tracks daily nutrition and provides insights and recommendations.

## Nutrition Strategies

The service includes modern nutrition strategies:

1. **Intermittent Fasting**: 16:8 eating windows for metabolic benefits
2. **Time-Restricted Eating**: Circadian rhythm-aligned meal timing
3. **Gut Health Focus**: Fermented foods and prebiotic emphasis
4. **Plant-Forward**: 75% plant-based with quality animal proteins

## Integration

### Environment Variables
- `PROMPT_CACHE_TABLE`: DynamoDB table for caching AI responses
- `USER_TABLE`: DynamoDB table for user profiles
- `NUTRITION_TABLE`: DynamoDB table for nutrition tracking
- `/ai-nutritionist/edamam/app-id`: Edamam API credentials
- `/ai-nutritionist/edamam/app-key`: Edamam API credentials

### Dependencies
- AWS Bedrock (amazon.titan-text-express-v1)
- AWS DynamoDB
- AWS Systems Manager Parameter Store
- Edamam API
- aiohttp for async HTTP requests

## Performance Optimizations

1. **Intelligent Caching**: 
   - 168-hour TTL for meal plans
   - 24-hour TTL for nutrition analysis
   - MD5-based cache keys for deterministic caching

2. **Cost Management**:
   - Cached AI responses reduce Bedrock costs by ~70%
   - Batched nutrition analysis
   - Optimized API call patterns

3. **User Experience**:
   - WhatsApp-optimized formatting
   - Progressive enhancement
   - Fallback mechanisms for API failures

## Usage Examples

### Generate Meal Plan
```python
service = ConsolidatedAINutritionService()
user_profile = {
    'user_id': 'user123',
    'dietary_restrictions': ['vegetarian'],
    'weekly_budget': 75,
    'fitness_goals': 'weight_loss'
}
meal_plan = service.generate_meal_plan(user_profile)
```

### Analyze Nutrition
```python
ingredients = ['1 cup quinoa', '1/2 cup black beans', '1 avocado']
nutrition = await service.analyze_meal_nutrition(ingredients, 'user123')
```

### Track Daily Nutrition
```python
daily_nutrition = DayNutrition(
    date='2024-01-15',
    kcal=1650,
    protein=85,
    water_cups=7
)
result = service.track_daily_nutrition('user123', daily_nutrition)
```

## Testing

Comprehensive test suite available in `tests/test_consolidated_ai_nutrition_service.py` covering:
- Service initialization
- Data model validation
- Meal plan generation
- Nutrition analysis
- Recipe search and formatting
- User profiling logic
- Caching mechanisms
- Error handling

## Migration Notes

This service consolidates the following files:
- `src/services/ai_service.py` → AI meal planning functionality
- `src/services/edamam_service.py` → Recipe search and nutrition analysis
- `src/services/nutrition_tracking_service.py` → Daily nutrition tracking
- `src/services/adaptive_meal_planning_service.py` → User adaptation
- `src/services/seamless_profiling_service.py` → User profiling

Handlers should be updated to use this consolidated service instead of the individual services.
