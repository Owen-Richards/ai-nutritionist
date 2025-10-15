import { MealPlan } from "@ai-health/schemas";

export const demoMealPlan: MealPlan = {
  id: "plan-demo",
  userId: "user-demo",
  weekOf: new Date().toISOString().slice(0, 10),
  days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((day, index) => ({
    date: new Date(Date.now() + index * 86400000).toISOString().slice(0, 10),
    meals: {
      breakfast: {
        id: `${day}-breakfast`,
        name: "Greek yogurt parfait",
        mealType: "breakfast",
        instructions: "Layer yogurt with berries and granola.",
        ingredients: ["Greek yogurt", "Blueberries", "Granola"]
      },
      lunch: {
        id: `${day}-lunch`,
        name: "Mediterranean quinoa bowl",
        mealType: "lunch",
        instructions: "Combine quinoa, chickpeas, veggies, tahini dressing.",
        ingredients: ["Quinoa", "Chickpeas", "Spinach", "Tomatoes"]
      },
      dinner: {
        id: `${day}-dinner`,
        name: "Salmon with roasted vegetables",
        mealType: "dinner",
        instructions: "Roast salmon with veggies at 400°F for 18 minutes.",
        ingredients: ["Salmon", "Broccoli", "Sweet potato"]
      }
    }
  }))
};

export const demoGroceries = [
  { name: "Greek yogurt", quantity: "5 cups", department: "Dairy" },
  { name: "Blueberries", quantity: "3 cups", department: "Produce" },
  { name: "Quinoa", quantity: "2 cups", department: "Grains" },
  { name: "Chickpeas", quantity: "4 cans", department: "Pantry" },
  { name: "Salmon", quantity: "5 fillets", department: "Seafood" }
];

export const demoEntitlements = {
  subscriptionPlan: "Premium",
  tokensRemaining: 120,
  renewalDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 14).toISOString().slice(0, 10),
  features: ["unlimited-plans", "grocery-deep-links", "advanced-logging"]
};
