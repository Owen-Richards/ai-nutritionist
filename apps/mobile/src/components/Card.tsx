import React from "react";
import { StyleSheet, View, ViewProps } from "react-native";
import { useTheme } from "@/providers/ThemeProvider";

export type CardProps = ViewProps & {
  elevated?: boolean;
  children: React.ReactNode;
};

export const Card: React.FC<CardProps> = ({ elevated = false, style, children, ...rest }) => {
  const { colors, radius, spacing } = useTheme();
  return (
    <View
      style={[
        styles.base,
        {
          backgroundColor: colors.surface,
          borderRadius: radius.md,
          padding: spacing.md,
          borderWidth: elevated ? 0 : StyleSheet.hairlineWidth,
          borderColor: colors.border,
          shadowColor: elevated ? colors.text : "transparent",
          shadowOpacity: elevated ? 0.12 : 0,
          shadowRadius: elevated ? 12 : 0,
          shadowOffset: elevated ? { width: 0, height: 8 } : { width: 0, height: 0 },
          elevation: elevated ? 4 : 0
        },
        style
      ]}
      {...rest}
    >
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  base: {
    width: "100%"
  }
});
