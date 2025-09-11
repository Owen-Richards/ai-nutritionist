# Multi-Goal & Custom Goal Examples

## 🎯 Complete Conversation Examples

### Example 1: Multiple Standard Goals

**User:** "I want to eat on a budget, build muscle, and improve gut health"

**System Response:**
```
Got it 👍 budget-friendly + muscle gain + gut health.

I'll focus on affordable, high-protein meals (chicken thighs, beans, lentils), include fermented foods and fiber for gut health, and keep everything within your budget cap.

Since you mentioned three goals, do you want me to prioritize budget, muscle, or gut health most strongly?

Ready for me to create your first multi-goal meal plan? 🍽️
```

**User:** "Budget is most important"

**System Response:**
```
Got it! I'll prioritize budget-friendly in your meal plans. 🎯
Want me to update your meal plan with these new priorities? 🔄
```

**User:** "Yes, create my meal plan"

**System Response:**
```
🎯 Here's your multi-goal plan balancing budget-friendly, muscle building, and gut health!
💰 Total cost: $22.50 (~$7.50/day)

💡 Smart trade-offs made:
• Budget focus may limit premium salmon, but I've maximized affordable protein sources like chicken thighs and lentils
• With multiple goals, some recipes may be good-but-not-perfect for each individual goal, but optimal for your overall needs

✅ Strongly optimized for: budget, muscle_gain

📅 **Day 1**
• **Breakfast**: Balanced Power Breakfast ($3.50, 8min, 18g protein)
• **Lunch**: Lentil & Egg Power Bowl ($2.50, 15min, 22g protein)  
• **Dinner**: Chicken Thigh & Bean Skillet ($3.25, 20min, 32g protein)

📅 **Day 2**
• **Breakfast**: Balanced Power Breakfast ($3.50, 8min, 18g protein)
• **Lunch**: Fermented Veggie & Quinoa Bowl ($4.75, 10min, 14g protein)
• **Dinner**: Chicken Thigh & Bean Skillet ($3.25, 20min, 32g protein)

📅 **Day 3**
• **Breakfast**: Balanced Power Breakfast ($3.50, 8min, 18g protein)
• **Lunch**: Lentil & Egg Power Bowl ($2.50, 15min, 22g protein)
• **Dinner**: Chicken Thigh & Bean Skillet ($3.25, 20min, 32g protein)

💡 You can:
• Rate meals (1-5 stars) to improve future plans
• Ask for substitutions: "swap the salmon for chicken"
• Request priority changes: "make budget more important"
• Track your meals: "ate breakfast" or "skipped lunch"
```

---

### Example 2: Custom Goal Handling

**User:** "skin health"

**System Response:**
```
I don't have a dedicated skin health tracker, but I can focus on omega-3s, antioxidants, and skin-supporting nutrients.

I'll learn what works for you as we go and adapt your meal suggestions!

Want me to create a meal plan that includes this goal? 🥗
```

**User:** "Yes please"

**System Response:**
```
🎯 Here's your skin health meal plan!

📅 **Day 1**
• **Breakfast**: Omega-3 Rich Smoothie Bowl ($4.25, 5min, 16g protein)
  High in: Vitamin C, Vitamin E, antioxidants
• **Lunch**: Salmon & Avocado Salad ($6.50, 10min, 28g protein)
  High in: Omega-3, healthy fats, zinc
• **Dinner**: Antioxidant Power Bowl ($5.75, 15min, 20g protein)
  High in: Beta-carotene, vitamin C, polyphenols

✨ Skin-supporting nutrients emphasized:
• Omega-3 fatty acids (salmon, walnuts, chia seeds)
• Vitamin C (berries, bell peppers, citrus)
• Vitamin E (nuts, seeds, avocado)
• Zinc (pumpkin seeds, chickpeas)
• Antioxidants (colorful vegetables, green tea)

💡 Track how your skin feels over the next few weeks! I'll learn what works best for you.
```

---

### Example 3: Goal Prioritization & Trade-offs

**User:** "I want quick meals but also want to build muscle"

**System Response:**
```
Perfect! I'll optimize for quick meals and muscle building.

Since you have multiple goals, which should I prioritize most strongly?

You can say something like:
• "Quick meals are most important"  
• "Muscle gain first, then speed"
• "Both equally important"

This helps me make better trade-offs in your meal plans! 🎯
```

**User:** "Quick meals first, but I still need protein"

**System Response:**
```
Got it! I'll prioritize quick & easy in your meal plans. 🎯

🎯 Here's your quick + muscle gain meal plan!

💡 Smart trade-offs made:
• Quick meal preference limits some nutrient-dense options, but 2 recipes can be meal-prepped
• Focusing on high-protein foods that cook fast: eggs, Greek yogurt, pre-cooked proteins

📅 **Day 1**
• **Breakfast**: Protein Power Smoothie ($3.25, 3min, 25g protein)
• **Lunch**: Quick Chicken & Rice Bowl ($4.50, 8min, 30g protein)
• **Dinner**: One-Pan Protein Pasta ($5.25, 12min, 28g protein)

⚡ All meals under 15 minutes prep time!
💪 Average 28g protein per meal hits your muscle building targets

Ready to get cooking? 🍳
```

---

### Example 4: Unknown Custom Goal

**User:** "brain health and focus"

**System Response:**
```
I'll track brain health and focus as a custom goal and adapt based on your feedback.

Here's what I can emphasize:
• Omega-3 rich foods (fatty fish, walnuts, chia seeds)
• Brain-supporting nutrients (blueberries, dark chocolate, nuts)
• Focus-enhancing foods (green tea, dark leafy greens)
• Stable blood sugar foods (complex carbs, protein, healthy fats)

I'll learn what specific foods help your mental clarity and adjust your meal plans accordingly!

Want me to create your first brain health meal plan? 🧠
```

---

### Example 5: Monetization Integration

**User:** "I have budget, muscle gain, gut health, and energy goals"

**System Response:**
```
🌟 **Unlock Multi-Goal Optimization**

You have 4 goals (budget, muscle building, gut health, energy). With Premium, I can:
• Create advanced meal plans that perfectly balance ALL your goals
• Provide detailed trade-off analysis and optimization  
• Give you priority access to new goal types and features
• Offer personalized coaching for complex nutrition needs

Ready to maximize your 4-goal nutrition strategy? Upgrade to Premium! 💪

[Continue with Free Plan] [Upgrade to Premium]
```

---

## 🔧 Technical Implementation Examples

### API Call Sequence for Multi-Goal Setup

1. **Add Multiple Goals**
```bash
POST /user/123/goals
{
  "goal_input": "budget and muscle gain",
  "priority": 3
}
```

2. **Update Priorities** 
```bash
PUT /user/123/goals/priorities
{
  "priority_updates": [
    {"goal_type": "budget", "priority": 4},
    {"goal_type": "muscle_gain", "priority": 2}
  ]
}
```

3. **Generate Multi-Goal Plan**
```bash
POST /user/123/meal-plan/multi-goal
{
  "days": 3
}
```

### Constraint Merging Example

**Input Goals:**
- Budget (Priority 4): max_cost_per_meal = $4.00
- Muscle Gain (Priority 3): protein_grams = 140
- Quick Meals (Priority 2): max_prep_time = 20 minutes

**Merged Constraints:**
```json
{
  "max_cost_per_meal": 4.00,
  "protein_grams": 140, 
  "max_prep_time": 20,
  "emphasized_foods": ["beans", "chicken_thighs", "eggs", "one_pot_meals"],
  "priority_weights": {
    "budget": 1.0,
    "muscle_gain": 0.75, 
    "quick_meals": 0.5
  }
}
```

### Custom Goal Proxy Mapping

**Input:** "sleep optimization"

**Proxy Mapping:**
```json
{
  "emphasized_foods": ["magnesium_rich", "tryptophan_rich", "herbal_teas"],
  "avoided_foods": ["caffeine_evening", "heavy_late_meals"],
  "description": "Include magnesium, avoid late caffeine, light evening meals",
  "nutrients_focus": ["magnesium", "tryptophan", "melatonin_precursors"]
}
```

---

## 🎮 User Experience Patterns

### Progressive Goal Discovery

Instead of overwhelming users with 20+ goal options, the system:

1. **Starts Simple**: "What's your main focus?"
2. **Discovers Naturally**: "I also want to save money" → Adds budget goal
3. **Suggests Related**: "Many users with muscle goals also focus on energy - interested?"
4. **Learns Continuously**: Meal ratings reveal hidden preferences

### Intelligent Trade-off Communication

❌ **Bad**: "Cannot satisfy budget and premium ingredient requirements"

✅ **Good**: "Budget focus may limit premium salmon, but I've maximized affordable protein sources like chicken thighs and lentils"

### Natural Priority Expression

Users can express priorities naturally:
- "Budget is more important than variety"
- "Quick meals first, nutrition second"  
- "I care most about muscle gain"
- "All goals equally important"

System translates to numerical priorities (1-4) for constraint resolution.

---

## 📊 Analytics & Learning

### Goal Trend Detection

**Trending Custom Goals** (promote to standard):
- "skin health" (12 users, 85% satisfaction)
- "sleep optimization" (8 users, 90% satisfaction)  
- "immune support" (6 users, 78% satisfaction)

### Successful Constraint Combinations

**High Success Patterns**:
- Budget + Quick Meals (92% satisfaction)
- Muscle Gain + Plant Forward (88% satisfaction)
- Energy + Gut Health (94% satisfaction)

**Challenging Combinations**:
- Budget + Gourmet Cooking (requires creative solutions)
- Quick Meals + Complex Nutrition Goals (needs meal prep strategies)

### User Feedback Integration

**Rating Analysis**:
- 5-star meals → Reinforce ingredient/cooking patterns
- 1-2 star meals → Identify problematic elements
- Substitution requests → Learn preference boundaries
- "Too expensive" feedback → Adjust budget sensitivity

This multi-goal system transforms nutrition coaching from generic advice to truly personalized, intelligent guidance that respects user priorities and real-world constraints.
