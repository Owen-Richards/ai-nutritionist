import { MutationKey, onlineManager, UseMutationOptions, UseMutationResult, useMutation } from "@tanstack/react-query";
import React from "react";

import { queueMutation, registerQueueHandler } from "@/data/offlineQueue";
import { useAppTranslation } from "@/i18n";
import { useFeedback } from "@/providers/FeedbackProvider";

export type QueuedMutationOptions<TData, TVariables, TError = Error, TContext = unknown> = UseMutationOptions<
  TData,
  TError,
  TVariables,
  TContext
> & {
  offlineMessage?: string;
  onQueued?: (variables: TVariables) => void;
};

export type QueuedMutationResult<TData, TVariables, TError = Error, TContext = unknown> = UseMutationResult<
  TData,
  TError,
  TVariables,
  TContext
> & {
  mutateAsyncQueued: (
    variables: TVariables,
    options?: Parameters<UseMutationResult<TData, TError, TVariables, TContext>["mutateAsync"]>[1]
  ) => Promise<TData | { queued: true }>;
};

export const useQueuedMutation = <TData, TVariables, TError = Error, TContext = unknown>(
  mutationKey: MutationKey,
  options: QueuedMutationOptions<TData, TVariables, TError, TContext>
): QueuedMutationResult<TData, TVariables, TError, TContext> => {
  const { offlineMessage, onQueued, ...mutationOptions } = options;
  const mutation = useMutation<TData, TError, TVariables, TContext>({
    mutationKey,
    ...mutationOptions
  });
  const mutateAsync = mutation.mutateAsync;
  const { notify } = useFeedback();
  const { t } = useAppTranslation("common");

  React.useEffect(() => {
    const unsubscribe = registerQueueHandler(mutationKey, async (variables) => {
      await mutateAsync(variables as TVariables);
    });
    return unsubscribe;
  }, [mutateAsync, mutationKey]);

  const mutateAsyncQueued = React.useCallback<QueuedMutationResult<TData, TVariables, TError, TContext>["mutateAsyncQueued"]>(
    async (variables, mutateOptions) => {
      if (!onlineManager.isOnline()) {
        await queueMutation(mutationKey, variables);
        onQueued?.(variables);
        notify(offlineMessage ?? t("states.offline"), { type: "info", haptic: "warning" });
        return { queued: true } as const;
      }
      return mutateAsync(variables, mutateOptions);
    },
    [mutationKey, mutateAsync, notify, offlineMessage, onQueued, t]
  );

  return {
    ...mutation,
    mutateAsyncQueued
  };
};
