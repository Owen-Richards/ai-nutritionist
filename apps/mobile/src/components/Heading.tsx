import React from "react";
import { StyleSheet, Text, TextProps } from "react-native";
import { useTheme } from "@/providers/ThemeProvider";

export type HeadingProps = TextProps & {
  level?: 1 | 2 | 3;
  children: React.ReactNode;
};

export const Heading: React.FC<HeadingProps> = ({ level = 1, style, children, ...rest }) => {
  const { colors, typography } = useTheme();
  const fontSize = level === 1 ? typography.display : level === 2 ? typography.title : typography.subtitle;

  return (
    <Text
      accessibilityRole="header"
      style={[styles.base, { fontSize, color: colors.text } , style]}
      {...rest}
    >
      {children}
    </Text>
  );
};

const styles = StyleSheet.create({
  base: {
    fontWeight: "600"
  }
});
