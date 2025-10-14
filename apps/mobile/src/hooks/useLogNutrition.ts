import { MutationKey } from "@tanstack/react-query";

import { useQueuedMutation } from "@/hooks/useQueuedMutation";
import { useApiClient } from "@/providers/ApiProvider";

export type NutritionLogInput = {
  note: string;
  category: string;
  timestamp: string;
};

const mutationKey: MutationKey = ["logs", "nutrition"];

type MutationResponse = {
  ok: true;
};

export const useLogNutrition = (offlineMessage: string) => {
  const client = useApiClient();
  return useQueuedMutation<MutationResponse, NutritionLogInput>(mutationKey, {
    mutationFn: async (input) => {
      await client.request("/logs", {
        method: "POST",
        body: JSON.stringify(input)
      });
      return { ok: true };
    },
    offlineMessage
  });
};
