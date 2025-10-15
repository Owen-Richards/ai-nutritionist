import React from "react";
import { Switch, View } from "react-native";

import { Button } from "@ai-health/ui";

import { Card } from "@/components/Card";
import { Heading } from "@/components/Heading";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Paragraph } from "@/components/Paragraph";
import { Screen } from "@/components/Screen";
import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";
import { useNotifications } from "@/providers/NotificationProvider";

export default function SettingsModal() {
  const { spacing } = useTheme();
  const { t } = useAppTranslation("profile");
  const { t: tCommon } = useAppTranslation();
  const notifications = useNotifications();
  const [notificationsEnabled, setNotificationsEnabled] = React.useState(false);

  const handleToggleNotifications = async () => {
    if (!notificationsEnabled) {
      const granted = await notifications.ensurePermissions();
      setNotificationsEnabled(granted);
    } else {
      setNotificationsEnabled(false);
    }
  };

  return (
    <Screen>
      <Heading level={1}>{t("language.title")}</Heading>
      <Paragraph>{t("language.description")}</Paragraph>
      <View style={{ marginBottom: spacing.md }}>
        <LanguageSwitcher />
      </View>

      <Card>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <View style={{ flex: 1, marginRight: spacing.md }}>
            <Heading level={3}>{t("notifications.title")}</Heading>
            <Paragraph>{t("notifications.description")}</Paragraph>
          </View>
          <Switch value={notificationsEnabled} onValueChange={handleToggleNotifications} />
        </View>
        <Button
          variant="secondary"
          style={{ marginTop: spacing.sm }}
          onPress={() => notifications.registerTestNotification()}
        >
          {tCommon("actions.enableNotifications")}
        </Button>
      </Card>

      <Card>
        <Heading level={3}>{t("beta.title")}</Heading>
        <Paragraph>{t("beta.description")}</Paragraph>
      </Card>
    </Screen>
  );
}
