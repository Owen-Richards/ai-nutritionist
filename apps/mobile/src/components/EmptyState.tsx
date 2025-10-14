import React from "react";
import { StyleSheet, View } from "react-native";
import { Button } from "@ai-health/ui";

import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { useTheme } from "@/providers/ThemeProvider";

export type EmptyStateProps = {
  title: string;
  message: string;
  actionLabel?: string;
  onActionPress?: () => void;
  testID?: string;
};

export const EmptyState: React.FC<EmptyStateProps> = ({ title, message, actionLabel, onActionPress, testID }) => {
  const { spacing } = useTheme();
  return (
    <View style={[styles.container, { gap: spacing.sm }]} testID={testID} accessibilityRole="text">
      <Heading level={3}>{title}</Heading>
      <Paragraph>{message}</Paragraph>
      {actionLabel && onActionPress ? (
        <Button variant="secondary" onPress={onActionPress}>
          {actionLabel}
        </Button>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: "flex-start"
  }
});
