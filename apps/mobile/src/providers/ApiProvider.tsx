import Constants from "expo-constants";
import React from "react";
import * as SecureStore from "expo-secure-store";
import { ApiClient, createApiClient } from "@ai-health/api-client";

const ApiContext = React.createContext<ApiClient | null>(null);

const getBaseUrl = () => {
  const fallback = "https://api.ai-nutritionist.test/v1";
  const extra = Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined;
  return extra?.apiBaseUrl ?? fallback;
};

async function getStoredToken(): Promise<string | undefined> {
  try {
    return (await SecureStore.getItemAsync("ai-health-access-token")) ?? undefined;
  } catch (error) {
    console.warn("Failed to read access token", error);
    return undefined;
  }
}

export const ApiProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const client = React.useMemo(
    () =>
      createApiClient({
        baseUrl: getBaseUrl(),
        getToken: getStoredToken
      }),
    []
  );

  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
};

export const useApiClient = () => {
  const context = React.useContext(ApiContext);
  if (!context) {
    throw new Error("useApiClient must be used within ApiProvider");
  }
  return context;
};
