import React from "react";
import { Pressable, StyleSheet, Text, ViewStyle } from "react-native";

type ButtonVariant = "primary" | "secondary";

type ButtonProps = {
  children: React.ReactNode;
  onPress?: () => void;
  variant?: ButtonVariant;
  style?: ViewStyle;
};

export const Button: React.FC<ButtonProps> = ({ children, onPress, variant = "primary", style }) => {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.base, styles[variant], pressed && styles.pressed, style]}
    >
      <Text style={styles.label}>{children}</Text>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  base: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center"
  },
  primary: {
    backgroundColor: "#2563eb"
  },
  secondary: {
    backgroundColor: "#0f172a"
  },
  pressed: {
    opacity: 0.85
  },
  label: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600"
  }
});
