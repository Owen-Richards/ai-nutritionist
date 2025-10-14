import React from "react";
import { View } from "react-native";
import { Button } from "@ai-health/ui";

import { useI18n } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";

export const LanguageSwitcher: React.FC = () => {
  const { availableLocales, locale, changeLocale } = useI18n();
  const { spacing } = useTheme();

  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: spacing.sm }}>
      {availableLocales.map(({ locale: code, label }) => (
        <Button
          key={code}
          variant={code === locale ? "primary" : "secondary"}
          onPress={() => changeLocale(code)}
        >
          {label}
        </Button>
      ))}
    </View>
  );
};
