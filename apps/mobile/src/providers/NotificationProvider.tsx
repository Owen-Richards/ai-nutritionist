import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import React from "react";
import { Alert } from "react-native";

import { useAppTranslation } from "@/i18n";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: false,
    shouldShowAlert: true,
    shouldSetBadge: false
  })
});

const NotificationContext = React.createContext<{
  ensurePermissions: () => Promise<boolean>;
  registerTestNotification: () => Promise<void>;
}>({
  ensurePermissions: async () => false,
  registerTestNotification: async () => {}
});

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { t } = useAppTranslation();

  React.useEffect(() => {
    Notifications.setNotificationChannelAsync("default", {
      name: "default",
      importance: Notifications.AndroidImportance.DEFAULT
    }).catch((error) => console.warn("Failed to set notification channel", error));

    Notifications.setNotificationCategoryAsync("meal-reminder", [
      {
        identifier: "LOG_MEAL",
        buttonTitle: "Log now"
      },
      {
        identifier: "SNOOZE",
        buttonTitle: "Snooze"
      }
    ]).catch((error) => console.warn("Failed to set notification category", error));
  }, []);

  const ensurePermissions = React.useCallback(async () => {
    const { status } = await Notifications.getPermissionsAsync();
    if (status === "granted") {
      return true;
    }

    return new Promise<boolean>((resolve) => {
      Alert.alert(t("notifications.prePromptTitle"), t("notifications.prePromptBody"), [
        {
          text: t("notifications.notNow"),
          style: "cancel",
          onPress: () => resolve(false)
        },
        {
          text: t("notifications.allow"),
          onPress: async () => {
            if (!Device.isDevice) {
              resolve(true);
              return;
            }
            const result = await Notifications.requestPermissionsAsync();
            resolve(result.granted);
          }
        }
      ]);
    });
  }, [t]);

  const registerTestNotification = React.useCallback(async () => {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: "AI Nutritionist",
        body: "Time to review your grocery list",
        categoryIdentifier: "meal-reminder"
      },
      trigger: { seconds: 5 }
    });
  }, []);

  const value = React.useMemo(
    () => ({
      ensurePermissions,
      registerTestNotification
    }),
    [ensurePermissions, registerTestNotification]
  );

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
};

export const useNotifications = () => React.useContext(NotificationContext);
