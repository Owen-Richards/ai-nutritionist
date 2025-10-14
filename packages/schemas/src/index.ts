import { z } from "zod";

export const GoalPreferenceSchema = z.object({
  id: z.string(),
  type: z.enum(["weight_loss", "weight_gain", "maintenance", "performance"]),
  targetCalories: z.number().positive(),
  proteinTarget: z.number().nonnegative().optional()
});

export const MealSchema = z.object({
  id: z.string(),
  name: z.string(),
  mealType: z.enum(["breakfast", "lunch", "dinner", "snack"]),
  instructions: z.string().optional(),
  ingredients: z.array(z.string()).default([])
});

export const DayPlanSchema = z.object({
  date: z.string(),
  meals: z.record(z.enum(["breakfast", "lunch", "dinner", "snack"]), MealSchema).optional()
});

export const MealPlanSchema = z.object({
  id: z.string(),
  userId: z.string(),
  weekOf: z.string(),
  days: z.array(DayPlanSchema)
});

export const UserProfileSchema = z.object({
  id: z.string(),
  name: z.string().optional(),
  email: z.string().email().optional(),
  phone: z.string().optional(),
  dietaryPreferences: z.array(z.string()).default([]),
  allergies: z.array(z.string()).default([]),
  budgetPerWeek: z.number().nonnegative().optional(),
  goals: z.array(GoalPreferenceSchema).default([])
});

export type MealPlan = z.infer<typeof MealPlanSchema>;
export type UserProfile = z.infer<typeof UserProfileSchema>;
