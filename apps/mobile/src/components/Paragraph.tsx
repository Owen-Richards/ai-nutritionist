import React from "react";
import { StyleSheet, Text, TextProps } from "react-native";
import { useTheme } from "@/providers/ThemeProvider";

export const Paragraph: React.FC<TextProps> = ({ style, children, ...rest }) => {
  const { colors, typography } = useTheme();
  return (
    <Text style={[styles.base, { color: colors.textMuted, fontSize: typography.body }, style]} {...rest}>
      {children}
    </Text>
  );
};

const styles = StyleSheet.create({
  base: {
    lineHeight: 22
  }
});
