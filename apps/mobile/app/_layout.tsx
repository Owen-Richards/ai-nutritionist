import { Stack } from "expo-router";
import React from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AppProviders } from "@/providers/AppProviders";
import { useAuth } from "@/providers/AuthProvider";
import { useAppTranslation } from "@/i18n";

const AuthenticatedStack = () => {
  const { t: tCommon } = useAppTranslation();
  const { t: tProfile } = useAppTranslation("profile");

  return (
    <Stack>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen
        name="(modals)/settings"
        options={{
          presentation: "modal",
          title: tProfile("language.title", { defaultValue: "Settings" }),
          headerLargeTitle: true,
          headerBackTitle: tCommon("actions.dismiss")
        }}
      />
    </Stack>
  );
};

const UnauthenticatedStack = () => (
  <Stack>
    <Stack.Screen name="(auth)" options={{ headerShown: false }} />
  </Stack>
);

const RouterGuard = () => {
  const { status } = useAuth();

  if (status === "checking") {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return status === "authenticated" ? <AuthenticatedStack /> : <UnauthenticatedStack />;
};

export default function RootLayout() {
  return (
    <AppProviders>
      <ErrorBoundary>
        <RouterGuard />
      </ErrorBoundary>
    </AppProviders>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center"
  }
});
