import React from "react";
import { AppState, Platform } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { focusManager } from "@tanstack/react-query";
import { StatusBar } from "expo-status-bar";

import { ConnectivityBanner } from "@/components/ConnectivityBanner";
import { markAppReady } from "@/observability/performance";
import { useColorScheme } from "@/hooks/useColorScheme";
import { I18nProvider } from "@/i18n";
import { ApiProvider } from "@/providers/ApiProvider";
import { AuthProvider } from "@/providers/AuthProvider";
import { DataProvider } from "@/providers/DataProvider";
import { FeedbackProvider } from "@/providers/FeedbackProvider";
import { NotificationProvider } from "@/providers/NotificationProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const mode = useColorScheme();

  React.useEffect(() => {
    if (Platform.OS === "web") return;
    const subscription = AppState.addEventListener("change", (status) => {
      focusManager.setFocused(status === "active");
    });
    return () => subscription.remove();
  }, []);

  React.useEffect(() => {
    markAppReady();
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <I18nProvider>
          <AuthProvider>
            <ApiProvider>
              <DataProvider>
                <ThemeProvider>
                  <NotificationProvider>
                    <FeedbackProvider>
                      <StatusBar style={mode === "dark" ? "light" : "dark"} />
                      <ConnectivityBanner />
                      {children}
                    </FeedbackProvider>
                  </NotificationProvider>
                </ThemeProvider>
              </DataProvider>
            </ApiProvider>
          </AuthProvider>
        </I18nProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
};
