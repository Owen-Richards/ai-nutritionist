import React from "react";
import { ScrollView, StyleSheet, View, ViewProps } from "react-native";
import { useTheme } from "@/providers/ThemeProvider";

export type ScreenProps = ViewProps & {
  scrollable?: boolean;
  children: React.ReactNode;
};

export const Screen: React.FC<ScreenProps> = ({ scrollable = true, style, children, ...rest }) => {
  const { colors, spacing } = useTheme();

  if (scrollable) {
    return (
      <ScrollView
        contentContainerStyle={[styles.scrollContent, { paddingHorizontal: spacing.lg, paddingVertical: spacing.lg }]}
        style={[styles.base, { backgroundColor: colors.background }]}
        {...rest}
      >
        {children}
      </ScrollView>
    );
  }

  return (
    <View style={[styles.base, { backgroundColor: colors.background, padding: spacing.lg }, style]} {...rest}>
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  base: {
    flex: 1
  },
  scrollContent: {
    paddingBottom: 64,
    gap: 24
  }
});
