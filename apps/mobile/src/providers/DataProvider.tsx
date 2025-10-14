import AsyncStorage from "@react-native-async-storage/async-storage";
import NetInfo from "@react-native-community/netinfo";
import { persistQueryClient } from "@tanstack/react-query-persist-client";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import { onlineManager, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { flushQueue } from "@/data/offlineQueue";
import { queryClient } from "@/utils/queryClient";

const persister = createAsyncStoragePersister({
  storage: AsyncStorage,
  key: "ai-health/query-cache",
  throttleTime: 2_000,
  serialize: JSON.stringify,
  deserialize: (value: string) => JSON.parse(value)
});

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isRestored, setRestored] = React.useState(false);

  React.useEffect(() => {
    let unsubscribed = false;
    persistQueryClient({
      queryClient,
      persister,
      maxAge: 1000 * 60 * 60 * 24,
      hydrateOptions: {
        defaultOptions: {
          queries: {
            staleTime: 1000 * 60 * 5
          }
        }
      }
    }).then(() => {
      if (!unsubscribed) {
        setRestored(true);
        flushQueue();
      }
    });
    return () => {
      unsubscribed = true;
    };
  }, []);

  React.useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const isOnline = Boolean(state.isConnected && state.isInternetReachable !== false);
      onlineManager.setOnline(isOnline);
      if (isOnline) {
        flushQueue();
      }
    });
    NetInfo.fetch().then((state) => {
      onlineManager.setOnline(Boolean(state.isConnected && state.isInternetReachable !== false));
    });
    return () => unsubscribe();
  }, []);

  if (!isRestored) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="small" />
      </View>
    );
  }

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
};

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center"
  }
});
