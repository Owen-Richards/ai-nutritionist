import React from "react";
import { RefreshControl, StyleSheet, View } from "react-native";
import { useLocalSearchParams } from "expo-router";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { Screen } from "@/components/Screen";
import { Skeleton, SkeletonLines } from "@/components/Skeleton";
import { useAppTranslation, useI18n } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";
import { useMealPlans } from "@/hooks/useApiData";
import { demoMealPlan } from "@/utils/sampleData";

export default function PlansScreen() {
  const { spacing, colors, radius } = useTheme();
  const { t } = useAppTranslation("plans");
  const { t: tCommon } = useAppTranslation();
  const { formatDate } = useI18n();
  const params = useLocalSearchParams<{ date?: string }>();
  const selectedDate = typeof params.date === "string" ? params.date : undefined;

  const mealPlans = useMealPlans();
  const isLoading = mealPlans.isPending;
  const plans = mealPlans.data && mealPlans.data.length > 0 ? mealPlans.data : [demoMealPlan];
  const hasEmpty = !isLoading && !mealPlans.isError && mealPlans.data && mealPlans.data.length === 0;

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
      <Paragraph>{t("description")}</Paragraph>

      {mealPlans.isError ? (
        <ErrorState
          title={t("error.title")}
          message={t("error.body")}
          onRetry={() => mealPlans.refetch()}
          primaryActionLabel={tCommon("actions.retry")}
        />
      ) : null}

      {hasEmpty ? <EmptyState title={t("empty.title")} message={t("empty.body")} /> : null}

      {isLoading && !mealPlans.data ? (
        <Card elevated>
          <Skeleton height={20} width="40%" />
          <View style={{ marginTop: spacing.md, gap: spacing.md }}>
            <SkeletonLines lines={3} />
            <SkeletonLines lines={3} />
          </View>
        </Card>
      ) : (
        plans.map((plan) => (
          <Card key={plan.id} elevated>
            <Heading level={2}>{formatDate(plan.weekOf, { month: "long", day: "numeric" })}</Heading>
            <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
              {plan.days.map((day) => {
                const isSelected = selectedDate && day.date === selectedDate;
                return (
                  <View
                    key={day.date}
                    style={[
                      styles.dayRow,
                      {
                        borderColor: isSelected ? colors.primary : colors.border,
                        backgroundColor: isSelected ? colors.primaryMuted : colors.surface,
                        borderRadius: radius.md,
                        padding: spacing.sm
                      }
                    ]}
                  >
                    <Paragraph style={styles.dayLabel}>
                      {formatDate(day.date, { weekday: "long" })}
                    </Paragraph>
                    <View style={{ gap: 4, flex: 1 }}>
                      {day.meals
                        ? Object.values(day.meals).map((meal) => (
                            <Paragraph key={meal.id} numberOfLines={1}>
                              {`${meal.mealType.toUpperCase()}: ${meal.name}`}
                            </Paragraph>
                          ))
                        : (
                          <Paragraph>{t("empty.body")}</Paragraph>
                        )}
                    </View>
                  </View>
                );
              })}
            </View>
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  dayRow: {
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: "row",
    gap: 12
  },
  dayLabel: {
    fontWeight: "600",
    width: 96
  }
});
