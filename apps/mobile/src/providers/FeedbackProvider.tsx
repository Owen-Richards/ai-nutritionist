import React from "react";
import { Animated, Easing, Pressable, StyleSheet, View } from "react-native";

import { Paragraph } from "@/components/Paragraph";
import { useTheme } from "@/providers/ThemeProvider";
import { announce } from "@/utils/accessibility";
import { haptics } from "@/utils/haptics";

export type FeedbackType = "success" | "warning" | "error" | "info";

export type FeedbackOptions = {
  type?: FeedbackType;
  durationMs?: number;
  announceMessage?: boolean;
  haptic?: keyof typeof haptics;
};

type FeedbackMessage = {
  id: number;
  message: string;
  options: FeedbackOptions;
};

type FeedbackContextValue = {
  notify: (message: string, options?: FeedbackOptions) => void;
};

const FeedbackContext = React.createContext<FeedbackContextValue | undefined>(undefined);

export const FeedbackProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { colors, radius, spacing } = useTheme();
  const [current, setCurrent] = React.useState<FeedbackMessage | null>(null);
  const translateY = React.useRef(new Animated.Value(-120)).current;
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const clear = React.useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    Animated.timing(translateY, {
      toValue: -120,
      duration: 200,
      easing: Easing.out(Easing.ease),
      useNativeDriver: true
    }).start(() => setCurrent(null));
  }, [translateY]);

  const notify = React.useCallback<FeedbackContextValue["notify"]>(
    (message, options) => {
      const payload: FeedbackMessage = {
        id: Date.now(),
        message,
        options: options ?? {}
      };
      setCurrent(payload);
      if (options?.haptic && haptics[options.haptic]) {
        haptics[options.haptic]!();
      }
      if (options?.announceMessage !== false) {
        announce(message);
      }
    },
    []
  );

  React.useEffect(() => {
    if (!current) {
      return;
    }
    Animated.timing(translateY, {
      toValue: 0,
      duration: 220,
      easing: Easing.out(Easing.ease),
      useNativeDriver: true
    }).start();
    timeoutRef.current = setTimeout(() => {
      clear();
    }, current.options.durationMs ?? 4000);
    return clear;
  }, [clear, current, translateY]);

  const background = React.useMemo(() => {
    if (!current) {
      return colors.surfaceElevated;
    }
    switch (current.options.type) {
      case "success":
        return colors.success;
      case "warning":
        return colors.warning;
      case "error":
        return colors.danger;
      default:
        return colors.info;
    }
  }, [colors, current]);

  return (
    <FeedbackContext.Provider value={{ notify }}>
      {children}
      {current ? (
        <Animated.View style={[styles.toastContainer, { transform: [{ translateY }] }]} pointerEvents="box-none">
          <Pressable onPress={clear} accessibilityRole="button" accessibilityLabel={current.message}>
            <View
              style={[
                styles.toast,
                {
                  backgroundColor: background,
                  borderRadius: radius.md,
                  paddingHorizontal: spacing.lg,
                  paddingVertical: spacing.sm
                }
              ]}
            >
              <Paragraph style={styles.toastText}>{current.message}</Paragraph>
            </View>
          </Pressable>
        </Animated.View>
      ) : null}
    </FeedbackContext.Provider>
  );
};

export const useFeedback = () => {
  const context = React.useContext(FeedbackContext);
  if (!context) {
    throw new Error("useFeedback must be used within FeedbackProvider");
  }
  return context;
};

const styles = StyleSheet.create({
  toastContainer: {
    position: "absolute",
    top: 16,
    left: 0,
    right: 0,
    alignItems: "center"
  },
  toast: {
    maxWidth: "90%",
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4
  },
  toastText: {
    fontWeight: "600",
    color: "#fff"
  }
});
