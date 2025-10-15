import { onlineManager } from "@tanstack/react-query";
import React from "react";
import { Animated, Easing, StyleSheet, View } from "react-native";

import { Paragraph } from "@/components/Paragraph";
import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";

type BannerState = "offline" | "online" | null;

export const ConnectivityBanner: React.FC = () => {
  const { colors, spacing } = useTheme();
  const { t } = useAppTranslation("common");
  const wasOffline = React.useRef(!onlineManager.isOnline());
  const [state, setState] = React.useState<BannerState>(wasOffline.current ? "offline" : null);
  const translateY = React.useRef(new Animated.Value(state ? 0 : -64)).current;

  React.useEffect(() => {
    let timeout: NodeJS.Timeout | null = null;
    const unsubscribe = onlineManager.subscribe((isOnline) => {
      if (!isOnline) {
        if (timeout) {
          clearTimeout(timeout);
          timeout = null;
        }
        wasOffline.current = true;
        setState("offline");
      } else if (wasOffline.current) {
        setState("online");
        timeout = setTimeout(() => {
          setState(null);
          timeout = null;
        }, 2500);
        wasOffline.current = false;
      } else {
        setState(null);
      }
    });
    return () => {
      unsubscribe();
      if (timeout) {
        clearTimeout(timeout);
      }
    };
  }, []);

  React.useEffect(() => {
    Animated.timing(translateY, {
      toValue: state ? 0 : -64,
      duration: 220,
      easing: Easing.out(Easing.ease),
      useNativeDriver: true
    }).start();
  }, [state, translateY]);

  const message = state === "offline" ? t("offlineBanner.message") : state === "online" ? t("states.online") : null;
  const backgroundColor = state === "online" ? colors.success : colors.warning;

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        styles.container,
        {
          transform: [{ translateY }]
        }
      ]}
    >
      {message ? (
        <View
          style={{
            backgroundColor,
            paddingHorizontal: spacing.lg,
            paddingVertical: spacing.sm,
            borderRadius: 999
          }}
          accessibilityLiveRegion="polite"
        >
          <Paragraph style={styles.text}>{message}</Paragraph>
        </View>
      ) : null}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 12,
    left: 0,
    right: 0,
    alignItems: "center",
    zIndex: 100
  },
  text: {
    color: "#fff",
    fontWeight: "600"
  }
});
