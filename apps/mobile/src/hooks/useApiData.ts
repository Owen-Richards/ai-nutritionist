import { useQuery } from "@tanstack/react-query";

import { useApiClient } from "@/providers/ApiProvider";
import { demoEntitlements, demoGroceries, demoMealPlan } from "@/utils/sampleData";
import { MealPlan } from "@ai-health/schemas";

type MealPlansResponse = MealPlan[];

type GroceryListResponse = {
  items: { name: string; quantity?: string; department?: string | null }[];
};

type EntitlementsResponse = typeof demoEntitlements;

export const useMealPlans = () => {
  const client = useApiClient();
  return useQuery<MealPlansResponse, Error>({
    queryKey: ["meal-plans"],
    queryFn: () => client.request<MealPlansResponse>("/plans"),
    placeholderData: [demoMealPlan]
  });
};

export const useGroceryList = () => {
  const client = useApiClient();
  return useQuery<GroceryListResponse, Error>({
    queryKey: ["grocery-list"],
    queryFn: () => client.request<GroceryListResponse>("/grocery-list"),
    placeholderData: { items: demoGroceries }
  });
};

export const useEntitlements = () => {
  const client = useApiClient();
  return useQuery<EntitlementsResponse, Error>({
    queryKey: ["entitlements"],
    queryFn: () => client.request<EntitlementsResponse>("/me/entitlements"),
    placeholderData: demoEntitlements
  });
};
