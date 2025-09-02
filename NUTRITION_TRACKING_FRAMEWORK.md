# Battle-Tested Nutrition Tracking Framework

## Overview

This document outlines a comprehensive nutrition tracking system designed for **nutrition power users** who want daily/weekly insights while maintaining a natural, non-intrusive experience. The system provides gentle feeling-checks and adaptive nudging based on actual usage patterns.

## Core Philosophy

- **Invisible Learning**: Track nutrition without feeling like interrogation
- **Battle-Tested UX**: Copy and patterns proven to work with real users
- **Adaptive Intelligence**: System learns and adapts based on user behavior
- **Modern Nutrition Science**: IF, gut health, plant-forward, anti-inflammatory strategies

## What We Track (Without Being Annoying)

### Automatic Inputs
- **Meal Status**: 1-tap tracking with "Ate it ✅ / Skipped ❌ / Modified ✍️"
- **Portions**: Quick slider with ½x, 1x, 1.5x, 2x options
- **Snacks**: Template buttons for fruit, yogurt, protein bar, nuts, custom
- **Water**: Glasses or oz/ml tracking
- **Movement**: Steps/workout flag (optional)
- **Wellness Check**: Emoji scale mood/energy/digestion/sleep (1 line)

### Computed Nutrients (Per Meal/Day/Week)
- **Macros**: kcal, protein, carbs, fat, fiber
- **Key Micros**: sodium, added sugar, potassium, calcium, iron, magnesium, omega-3
- **Dietary Markers**: plant-protein %, whole-grain %, ultra-processed flag, CO₂ estimate

## Nutrition Computation Engine

### 1. Grounded Recipes (Preferred)
Link each dish to a recipe with known nutrition data from internal DB or API.

### 2. Fallback Estimation
Ingredient list → per-ingredient nutrition → sum → scale by portion.

### 3. User Adjustments
If they substitute (chicken→tofu) or add cheese, re-compute differences dynamically.

**Performance Tip**: Cache per-meal nutrition and only re-calculate on substitutions or portion changes.

## Daily & Weekly Outputs

### Daily Recap (Auto 8-9pm Local)
```
Today: **1,840 kcal** • **124g protein** • **31g fiber** • **1,850mg sodium**
✅ Hit protein 🎯; ⚠️ Fiber a bit low vs 35g goal.
Water: 6 cups | Steps: ~8k | Mood: 🙂 Energy: ⚡ Digestion: 👍
```

### Weekly Report (Sunday Evening)
```
This week avg: **1,910 kcal/d**, **128g protein/d**, **33g fiber/d**, **1,920mg sodium/d**
Wins: +14g protein over goal, higher whole-grain ratio.
Tweaks: Fiber +2g/day, reduce added sugar at breakfast.
Highlights you loved: Miso-ginger salmon (5⭐), Harissa chickpeas (4⭐).
Next week plan: keep protein; add berries/oats breakfast 2×; swap one dessert for fruit + yogurt.
```

### On-Demand Commands
- `"stats today"` - Current day breakdown with traffic lights
- `"weekly report"` - Comprehensive week analysis
- `"macro breakdown"` - Detailed macro percentages
- `"fiber sources"` - Suggested high-fiber foods
- `"low-sodium swaps"` - Salt reduction alternatives

## Feeling-Check System (Gentle & Adaptive)

### Micro Daily Check (2 Taps, Optional)
**"How did you feel today?"**
- Mood: 😞 😐 🙂 😄 
- Energy: 💤 ⚡ 
- Digestion: 😣 🙂 👍 
- Sleep: 😴😴😴

If user responds → store + learn. If not → no nagging.

### Adaptive Responses

#### If Feeling ↓ (2+ Days in Row)
**"I noticed energy's been low. Want to try one of these?"**
- +15–25g protein earlier in the day
- Higher-fiber breakfast (oats/berries) to stabilize appetite
- Shift dinner lighter & earlier (time-restricted window)
- Hydration nudge: +2 cups water before 2pm
- Swap refined carbs at lunch → whole grain/legume base

#### If Feeling ↑ (2-3 Days)
**"Nice streak! Lock it in?"**
- Keep current timing window (e.g., 16:8) for another week
- Repeat top 2 high-satisfaction dinners next week
- Introduce one new gut-friendly add-on (kefir/kimchi) 2×

## Strategy Suggestions (Opt-In, Evidence-Informed)

### Intermittent Fasting / Time-Restricted Eating
Suggest 12:12 → 14:10 → 16:8 gradually if they often skip breakfast or report late-night reflux/poor sleep.

### Protein Timing
Front-load 25–40g at breakfast/lunch for satiety and energy.

### Fiber Ramp
Add +5g/week until 30–38g/d; pair with water to avoid GI discomfort.

### Sodium Trims
Target 1,500–2,000mg/d if they flag BP/"puffy" feeling; propose herb/acid swaps.

### Plant-Forward Swaps
1–3 dinners/wk → legumes or tofu; keep bold flavors they like.

### Gut-Friendly
Rotate prebiotics (onion, garlic, oats, bananas, legumes) and fermented foods 2–4×/wk.

**Always framed as OPTIONS. Never medical advice; remind users to consult clinician for specific conditions.**

## Adaptation Playbooks (Automatic Triggers)

### Protein Below Target ≥3 Days
Add 1 easy protein snack/day (Greek yogurt, edamame, tuna packet).

### Fiber <25g Average
Oats/berries breakfast 2×, legume lunch 2×, veg add-on at dinner.

### Sodium >2,300mg Average
Swap canned for low-sodium, boost citrus/herbs/umami; cut 1 processed item.

### Energy Low + Afternoon Crashes
Reduce refined carbs at lunch; add protein + crunch + acid; hydrate.

### Evening Hunger Spikes
Shift more calories to earlier meals; add volume (veg/soup/salad) to dinner.

### Bloating Flagged
Reduce sugar alcohols/carbonation; try low-FODMAP swaps temporarily; increase walking post-meal.

## Battle-Tested UX Copy

### Daily Nudge (Morning)
```
Goal today: **120g protein**, **30g fiber**, water **8 cups**. 
I'll pace your meals to make that easy.
```

### Pre-Dinner Reminder (If Behind Targets)
```
You're at 70g protein, 18g fiber — adding lentils or a yogurt 
dessert would hit targets.
```

### "Stats Today" Reply
Concise line with traffic-light markers (🟢 on target / 🟡 close / 🔴 off).

### "How Can I Feel Better?" Reply
3 personalized, low-effort tweaks referencing their data (timing, swaps, hydration, sleep pad).

## Data Model Additions

### DayNutrition
```python
{
    date: str,
    kcal: float, protein: float, carbs: float, fat: float, 
    fiber: float, sodium: float, sugar_added: float,
    water: float, steps: int?,
    mood: str?, energy: str?, digestion: str?, sleep_quality: str?,
    meals_ate: list, meals_skipped: list, meals_modified: list, snacks: list
}
```

### WeekSummary
```python
{
    averages: dict, deltas_vs_goals: dict, 
    wins: list, tweaks: list, top_liked_meals: list
}
```

### UserFlags
```python
{
    low_energy_streak: int, high_sodium_week: bool, fiber_gap: bool,
    late_eating_pattern: bool, good_streak: int
}
```

### Interventions
```python
{
    date: str, type: str, description: str, result_after_7d: str?
}
```

## Privacy & Safety

- Keep mood/health notes **local to user record**; never share
- Don't infer or label medical conditions
- Standard footer on reports: *"General wellness guidance, not medical advice."*

## User Type Customization

### Casual Users
Default to weekly report only; daily check-in off.

### Nutrition Nerds
Enable daily stats, macro targets, and IF window guidance.

### Family Cooks
Show **household** protein/fiber coverage and per-member notes (e.g., kid fiber boost).

### Dinner Party Weeks
Skip daily stats; provide menu timeline & next-day lighter reset plan.

## Implementation Status

### ✅ Completed Components

1. **NutritionTrackingService** (`src/services/nutrition_tracking_service.py`)
   - Complete meal tracking with 1-tap interface
   - Daily/weekly reports with traffic light indicators
   - Feeling check system with emoji scales
   - Adaptive suggestion engine
   - Modern nutrition computation

2. **NutritionMessagingService** (`src/services/nutrition_messaging_service.py`)
   - Battle-tested UX copy for all interactions
   - Natural language parsing for tracking inputs
   - Contextual response generation
   - Strategy suggestion templates
   - Privacy-compliant messaging

3. **Universal Message Handler Integration** (`src/handlers/universal_message_handler.py`)
   - Nutrition tracking as first-priority conversation handling
   - Quick commands: "stats today", "weekly report", "how can I feel better?"
   - Natural language meal/water/feeling tracking
   - Seamless integration with existing meal planning

### 🎯 Key Features Implemented

- **1-Tap Meal Tracking**: "Ate it ✅ / Skipped ❌ / Modified ✍️"
- **Smart Portion Control**: ½x, 1x, 1.5x, 2x multipliers
- **Template Snack Buttons**: Fruit, yogurt, protein bar, nuts, custom
- **Natural Water Logging**: "2 cups water", "16 oz", "500ml"
- **Emoji Feeling Scales**: Mood, energy, digestion tracking
- **Traffic Light Stats**: 🟢🟡🔴 indicators for quick status
- **Adaptive Nudging**: Low energy suggestions, good streak reinforcement
- **Modern Nutrition Strategies**: IF, gut health, plant-forward, anti-inflammatory
- **Privacy-First Design**: Local storage, no medical claims, opt-in tracking

## Quick Commands Reference

```
# Daily Tracking
"ate breakfast" / "skipped lunch" / "modified dinner"
"2 cups water" / "16 oz" / "500ml" 
"feeling tired" / "high energy" / "good mood"

# Reports & Stats  
"stats today" - Daily recap with traffic lights
"weekly report" - Comprehensive week summary
"macro breakdown" - Detailed macro percentages
"fiber sources" - High-fiber food suggestions
"sodium swaps" - Low-sodium alternatives

# Feeling Better
"how can I feel better?" - Personalized suggestions based on data
"morning goals" - Daily targets and motivation
"feel better" - Quick improvement tips

# Strategy Information
"intermittent fasting" - IF guidance and timing
"gut health" - Fermented food and prebiotic suggestions  
"plant forward" - Plant protein alternatives
```

## Usage Examples

### Morning Interaction
```
User: "morning goals"
AI: "Goal today: **120g protein**, **30g fiber**, water **8 cups**. 
    I'll pace your meals to make that easy."
```

### Meal Tracking
```
User: "ate breakfast" 
AI: "Got it! Marked breakfast as ate."

User: "2 cups water"
AI: "Hydration logged! 2.0/8 cups (25%) 💧"
```

### Daily Check-In
```
User: "stats today"
AI: "Today: **1,840 kcal** • **124g protein** • **31g fiber** • **1,850mg sodium**
    ✅ Hit protein 🎯; ⚠️ Fiber a bit low vs 35g goal.
    Water: 6 cups | Mood: 🙂 Energy: ⚡
    
    **Quick status:** 🟢 Protein | 🟡 Fiber | 🟢 Water"
```

### Adaptive Suggestions
```
User: "how can I feel better?"
AI: "Based on your recent data, try these:

    **1.** Add 1 easy protein snack/day (Greek yogurt, edamame)
    **2.** Higher-fiber breakfast (oats/berries) to stabilize appetite  
    **3.** Hydration nudge: +2 cups water before 2pm
    
    Pick what feels most doable right now! 😊"
```

This framework transforms nutrition tracking from a chore into an intelligent, supportive conversation that actually helps users feel better and eat healthier. The key is making it feel like guidance from a knowledgeable friend rather than data collection from an app.

## Next Steps for Enhancement

1. **Smart Timing**: Auto-schedule daily recaps based on user's typical dinner time
2. **Photo Recognition**: Allow meal photo uploads for automatic nutrition estimation  
3. **Integration Hooks**: Connect with fitness trackers for step/sleep data
4. **Family Modes**: Household nutrition tracking and kid-friendly interfaces
5. **Meal Plan Integration**: Auto-populate tracking from planned meals
6. **Advanced Analytics**: Correlation analysis between feelings and nutrition patterns
