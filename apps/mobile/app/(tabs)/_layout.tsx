import { Tabs } from "expo-router";
import React from "react";
import { Ionicons } from "@expo/vector-icons";

import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";

const iconMap: Record<string, keyof typeof Ionicons.glyphMap> = {
  today: "sunny",
  plans: "calendar",
  groceries: "cart",
  track: "pulse",
  profile: "person"
};

export default function TabsLayout() {
  const { colors } = useTheme();
  const { t } = useAppTranslation("common");

  const labels = React.useMemo(
    () => ({
      today: t("navigation.today"),
      plans: t("navigation.plans"),
      groceries: t("navigation.groceries"),
      track: t("navigation.track"),
      profile: t("navigation.profile")
    }),
    [t]
  );

  return (
    <Tabs
      initialRouteName="today"
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border
        },
        tabBarLabel: labels[route.name] ?? route.name,
        tabBarIcon: ({ color, size }) => {
          const iconName = iconMap[route.name] ?? "ellipse";
          return <Ionicons name={iconName as never} color={color} size={size} />;
        }
      })}
    >
      <Tabs.Screen name="today" options={{ title: labels.today }} />
      <Tabs.Screen name="plans" options={{ title: labels.plans }} />
      <Tabs.Screen name="groceries" options={{ title: labels.groceries }} />
      <Tabs.Screen name="track" options={{ title: labels.track }} />
      <Tabs.Screen name="profile" options={{ title: labels.profile }} />
    </Tabs>
  );
}
