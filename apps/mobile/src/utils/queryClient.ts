import { QueryClient } from "@tanstack/react-query";

type MaybeApiError = {
  status?: number;
  message?: string;
};

const isNetworkError = (error: unknown) => {
  if (!error) return false;
  if (typeof error === "string") {
    return error.toLowerCase().includes("network");
  }
  const maybe = error as MaybeApiError & { code?: string };
  return maybe.code === "ECONNABORTED" || maybe.code === "ERR_NETWORK" || maybe.message?.includes("Network") === true;
};

const shouldRetry = (failureCount: number, error: unknown) => {
  const maybe = error as MaybeApiError | undefined;
  if (maybe?.status && maybe.status >= 400 && maybe.status < 500) {
    return false;
  }
  if (isNetworkError(error)) {
    return failureCount < 3;
  }
  return failureCount < 2;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 60 * 24,
      retry: shouldRetry,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true
    },
    mutations: {
      retry: shouldRetry
    }
  }
});
