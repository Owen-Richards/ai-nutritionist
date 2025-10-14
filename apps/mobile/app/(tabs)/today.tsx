import React from "react";
import { RefreshControl, View } from "react-native";
import { Link } from "expo-router";
import { Button } from "@ai-health/ui";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { Screen } from "@/components/Screen";
import { Skeleton, SkeletonLines } from "@/components/Skeleton";
import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";
import { useEntitlements, useMealPlans } from "@/hooks/useApiData";
import { demoMealPlan } from "@/utils/sampleData";

export default function TodayScreen() {
  const { spacing, colors } = useTheme();
  const { t } = useAppTranslation("today");
  const { t: tCommon } = useAppTranslation();

  const mealPlans = useMealPlans();
  const entitlements = useEntitlements();

  const isLoading = mealPlans.isPending || entitlements.isPending;
  const planFromApi = mealPlans.data && mealPlans.data.length > 0 ? mealPlans.data[0] : undefined;
  const plan = planFromApi ?? demoMealPlan;
  const firstDay = plan?.days?.[0];
  const meals = firstDay ? Object.values(firstDay.meals ?? {}) : [];
  const hasEmptyPlan = !isLoading && !mealPlans.isError && (!mealPlans.data || mealPlans.data.length === 0);

  return (
    <Screen
      refreshControl={
        <RefreshControl
          tintColor={colors.primary}
          colors={[colors.primary]}
          refreshing={mealPlans.isRefetching}
          onRefresh={() => mealPlans.refetch()}
        />
      }
    >
      <Heading level={1}>{t("title")}</Heading>
      <Paragraph>
        {entitlements.data
          ? t("subscriptionSummary", {
              plan: entitlements.data.subscriptionPlan,
              tokens: entitlements.data.tokensRemaining
            })
          : t("noNameSummary", { plan: "" })}
      </Paragraph>

      {mealPlans.isError ? (
        <ErrorState
          title={t("error.title")}
          message={t("error.body")}
          onRetry={() => mealPlans.refetch()}
          primaryActionLabel={tCommon("actions.retry")}
        />
      ) : null}

      {hasEmptyPlan ? (
        <EmptyState title={t("empty.title")} message={t("empty.body")} />
      ) : (
        <Card elevated>
          <Heading level={2}>{t("nextPlanHeading")}</Heading>
          {isLoading && !planFromApi ? (
            <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
              <Skeleton height={18} width="60%" />
              <SkeletonLines lines={3} />
            </View>
          ) : (
            <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
              {meals.map((meal) => (
                <View key={meal.id} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Paragraph style={{ fontWeight: "600", color: colors.primary }}>
                    {meal.mealType}
                  </Paragraph>
                  <Paragraph style={{ flex: 1, textAlign: "right" }}>{meal.name}</Paragraph>
                </View>
              ))}
            </View>
          )}
          <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
            <Link href="/(tabs)/plans" asChild>
              <Button testID="nav-plans">{t("viewPlanCta")}</Button>
            </Link>
            <Link href="/(tabs)/groceries" asChild>
              <Button variant="secondary" testID="nav-groceries">
                {t("reviewGroceriesCta")}
              </Button>
            </Link>
          </View>
        </Card>
      )}

      <Card>
        <Heading level={2}>{t("actionsHeading")}</Heading>
        <View style={{ marginTop: spacing.sm, gap: spacing.sm }}>
          <Link href="/(tabs)/track" asChild>
            <Button variant="secondary" testID="quick-action-track">
              {t("logMealCta")}
            </Button>
          </Link>
        </View>
      </Card>

      <Card>
        <Heading level={2}>{t("insightsHeading")}</Heading>
        {isLoading ? (
          <View style={{ marginTop: spacing.sm }}>
            <SkeletonLines lines={2} />
          </View>
        ) : (
          <Paragraph style={{ marginTop: spacing.sm }}>{t("insightsCopy")}</Paragraph>
        )}
      </Card>
    </Screen>
  );
}
