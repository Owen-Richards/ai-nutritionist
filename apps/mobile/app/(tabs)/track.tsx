import React from "react";
import { StyleSheet, TextInput, View } from "react-native";
import { useLocalSearchParams } from "expo-router";

import { Button } from "@ai-health/ui";

import { Card } from "@/components/Card";
import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { Screen } from "@/components/Screen";
import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";
import { useFeedback } from "@/providers/FeedbackProvider";
import { NutritionLogInput, useLogNutrition } from "@/hooks/useLogNutrition";

export default function TrackScreen() {
  const { spacing, colors, radius } = useTheme();
  const { t } = useAppTranslation("track");
  const { t: tCommon } = useAppTranslation();
  const { notify } = useFeedback();
  const params = useLocalSearchParams<{ quick?: string }>();
  const inputRef = React.useRef<TextInput>(null);
  const [note, setNote] = React.useState("");

  const mutation = useLogNutrition(t("pendingSync"));
  const quickActions = t("quickActions", { returnObjects: true }) as string[];

  React.useEffect(() => {
    if (params.quick === "true") {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [params.quick]);

  const handleSubmit = async () => {
    if (!note.trim()) {
      notify(t("error"), { type: "warning", haptic: "warning" });
      return;
    }

    const payload: NutritionLogInput = {
      note: note.trim(),
      category: "note",
      timestamp: new Date().toISOString()
    };

    try {
      await mutation.mutateAsyncQueued(payload);
      setNote("");
      notify(t("queued"), { type: "success", haptic: "success" });
    } catch (error) {
      console.warn("log submit failed", error);
      notify(t("error"), { type: "error", haptic: "error" });
    }
  };

  return (
    <Screen>
      <Heading level={1}>{t("title")}</Heading>
      <Paragraph>{t("description")}</Paragraph>

      <Card elevated>
        <Heading level={2}>{t("quickAdd")}</Heading>
        <View style={[styles.quickButtons, { marginTop: spacing.sm }]}>
          {quickActions.map((label) => (
            <Button key={label} variant="secondary" onPress={() => setNote(`${label}: `)}>
              {label}
            </Button>
          ))}
        </View>
        <Paragraph style={{ marginTop: spacing.md }}>{t("noteLabel")}</Paragraph>
        <TextInput
          ref={inputRef}
          placeholder={t("notePlaceholder")}
          value={note}
          onChangeText={setNote}
          style={{
            minHeight: 120,
            backgroundColor: colors.surfaceElevated,
            borderRadius: radius.md,
            padding: spacing.md,
            borderColor: colors.border,
            borderWidth: StyleSheet.hairlineWidth,
            textAlignVertical: "top"
          }}
          multiline
          accessibilityLabel={t("noteLabel")}
        />
        <View style={{ marginTop: spacing.md }}>
          <Button onPress={handleSubmit} disabled={mutation.isPending}>
            {mutation.isPending ? tCommon("states.loading") : t("submit")}
          </Button>
        </View>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  quickButtons: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12
  }
});
