import React from "react";
import { View } from "react-native";
import { Link } from "expo-router";
import { Button } from "@ai-health/ui";

import { Card } from "@/components/Card";
import { Heading } from "@/components/Heading";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Paragraph } from "@/components/Paragraph";
import { Screen } from "@/components/Screen";
import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";
import { useEntitlements } from "@/hooks/useApiData";
import { useAuth } from "@/providers/AuthProvider";

export default function ProfileScreen() {
  const { spacing } = useTheme();
  const { t } = useAppTranslation("profile");
  const { t: tCommon } = useAppTranslation();
  const entitlements = useEntitlements();
  const { signOut, user } = useAuth();

  return (
    <Screen scrollable={false}>
      <Heading level={1}>{t("title")}</Heading>
      <Paragraph>{t("description")}</Paragraph>

      <Card elevated>
        <Heading level={2}>{t("subscription.title")}</Heading>
        <Paragraph>
          {t("subscription.plan")}: {entitlements.data?.subscriptionPlan ?? "—"}
        </Paragraph>
        <Paragraph>
          {t("subscription.tokens")}: {entitlements.data?.tokensRemaining ?? 0}
        </Paragraph>
        <Paragraph>
          {t("subscription.renews")}: {entitlements.data?.renewalDate ?? "—"}
        </Paragraph>
        <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
          <Button onPress={() => console.log("manage subscription")}>{t("subscription.manage")}</Button>
          <Link href="/(modals)/settings" asChild>
            <Button variant="secondary">{tCommon("actions.openSettings")}</Button>
          </Link>
        </View>
      </Card>

      <Card>
        <Heading level={2}>{t("language.title")}</Heading>
        <Paragraph>{t("language.description")}</Paragraph>
        <View style={{ marginTop: spacing.sm }}>
          <LanguageSwitcher />
        </View>
      </Card>

      <Card>
        <Heading level={2}>{t("notifications.title")}</Heading>
        <Paragraph>{t("notifications.description")}</Paragraph>
      </Card>

      <Card>
        <Heading level={2}>{t("beta.title")}</Heading>
        <Paragraph>{t("beta.description")}</Paragraph>
      </Card>

      <Paragraph>{user?.email}</Paragraph>
      <Button variant="secondary" onPress={signOut}>
        {tCommon("actions.signOut")}
      </Button>
    </Screen>
  );
}
