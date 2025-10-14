import * as Haptics from "expo-haptics";
import { Platform } from "react-native";

const isHapticsSupported = Platform.OS === "ios" || Platform.OS === "android";

type ImpactStyle = keyof typeof Haptics.ImpactFeedbackStyle;

type NotificationType = keyof typeof Haptics.NotificationFeedbackType;

const triggerImpact = (style: ImpactStyle = "Medium") => {
  if (!isHapticsSupported) return;
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle[style]).catch((error) => {
    console.warn("Haptics impact failed", error);
  });
};

const triggerNotification = (type: NotificationType = "Success") => {
  if (!isHapticsSupported) return;
  Haptics.notificationAsync(Haptics.NotificationFeedbackType[type]).catch((error) => {
    console.warn("Haptics notification failed", error);
  });
};

export const haptics = {
  light: () => triggerImpact("Light"),
  medium: () => triggerImpact("Medium"),
  heavy: () => triggerImpact("Heavy"),
  success: () => triggerNotification("Success"),
  warning: () => triggerNotification("Warning"),
  error: () => triggerNotification("Error")
};

export const useHaptics = () => haptics;
