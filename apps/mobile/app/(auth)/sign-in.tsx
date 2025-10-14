import React from "react";
import { Screen } from "@/components/Screen";
import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { useTheme } from "@/providers/ThemeProvider";
import { Button } from "@ai-health/ui";
import { useAuth } from "@/providers/AuthProvider";
import { useAppTranslation } from "@/i18n";

export default function SignInScreen() {
  const { signIn } = useAuth();
  const { spacing } = useTheme();
  const { t } = useAppTranslation();

  const handleSignIn = React.useCallback(() => {
    signIn("demo-token").catch((error) => {
      console.warn("Demo sign-in failed", error);
    });
  }, [signIn]);

  return (
    <Screen>
      <Heading level={1}>{t("appName")}</Heading>
      <Paragraph>
        We use secure links to authenticate. For now, tap below to explore the demo experience.
      </Paragraph>
      <Button style={{ marginTop: spacing.lg }} onPress={handleSignIn}>
        {t("actions.signIn")}
      </Button>
    </Screen>
  );
}
