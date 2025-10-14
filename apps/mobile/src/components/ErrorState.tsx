import React from "react";
import { StyleSheet, View } from "react-native";
import { Button } from "@ai-health/ui";

import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { useTheme } from "@/providers/ThemeProvider";

export type ErrorStateProps = {
  title: string;
  message: string;
  onRetry?: () => void;
  primaryActionLabel?: string;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
  testID?: string;
};

export const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  message,
  onRetry,
  primaryActionLabel = "Retry",
  secondaryActionLabel,
  onSecondaryAction,
  testID
}) => {
  const { spacing } = useTheme();
  return (
    <View style={[styles.container, { gap: spacing.sm }]} testID={testID} accessibilityRole="alert">
      <Heading level={3}>{title}</Heading>
      <Paragraph>{message}</Paragraph>
      <View style={[styles.actions, { marginTop: spacing.sm }]}>
        {onRetry ? <Button onPress={onRetry}>{primaryActionLabel}</Button> : null}
        {onSecondaryAction && secondaryActionLabel ? (
          <Button variant="secondary" onPress={onSecondaryAction}>
            {secondaryActionLabel}
          </Button>
        ) : null}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: "flex-start"
  },
  actions: {
    flexDirection: "row",
    gap: 12
  }
});
