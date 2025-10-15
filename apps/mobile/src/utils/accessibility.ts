import React from "react";
import { AccessibilityInfo, findNodeHandle } from "react-native";

export const announce = async (message: string) => {
  try {
    await AccessibilityInfo.announceForAccessibility(message);
  } catch (error) {
    console.warn("Accessibility announce failed", error);
  }
};

export const focusOnRef = (ref: React.RefObject<unknown>) => {
  const node = findNodeHandle(ref.current);
  if (node) {
    AccessibilityInfo.setAccessibilityFocus(node);
  }
};
