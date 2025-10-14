import React from "react";
import { RefreshControl, View } from "react-native";
import { Button } from "@ai-health/ui";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Heading } from "@/components/Heading";
import { Paragraph } from "@/components/Paragraph";
import { Screen } from "@/components/Screen";
import { SkeletonLines } from "@/components/Skeleton";
import { useAppTranslation } from "@/i18n";
import { useTheme } from "@/providers/ThemeProvider";
import { useGroceryList } from "@/hooks/useApiData";
import { demoGroceries } from "@/utils/sampleData";

export default function GroceriesScreen() {
  const { spacing, colors } = useTheme();
  const { t } = useAppTranslation("groceries");
  const { t: tCommon } = useAppTranslation();
  const groceriesQuery = useGroceryList();
  const isLoading = groceriesQuery.isPending;
  const items = groceriesQuery.data?.items ?? demoGroceries;
  const hasEmpty = !isLoading && !groceriesQuery.isError && groceriesQuery.data?.items.length === 0;

  return (
    <Screen
      refreshControl={
        <RefreshControl
          tintColor={colors.primary}
          colors={[colors.primary]}
          refreshing={groceriesQuery.isRefetching}
          onRefresh={() => groceriesQuery.refetch()}
        />
      }
    >
      <Heading level={1}>{t("title")}</Heading>
      <Paragraph>{t("description")}</Paragraph>

      {groceriesQuery.isError ? (
        <ErrorState
          title={t("error.title")}
          message={t("error.body")}
          onRetry={() => groceriesQuery.refetch()}
          primaryActionLabel={tCommon("actions.retry")}
        />
      ) : null}

      {hasEmpty ? <EmptyState title={t("empty.title")} message={t("empty.body")} /> : null}

      <Card elevated>
        <Heading level={2}>{t("thisWeek")}</Heading>
        {isLoading && !groceriesQuery.data ? (
          <View style={{ marginTop: spacing.md }}>
            <SkeletonLines lines={4} />
          </View>
        ) : (
          <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
            {items.map((item) => (
              <View key={`${item.name}-${item.department ?? ""}`} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                <Paragraph style={{ fontWeight: "500" }}>{item.name}</Paragraph>
                <Paragraph style={{ color: colors.textMuted }}>
                  {[item.quantity, item.department].filter(Boolean).join(" · ")}
                </Paragraph>
              </View>
            ))}
          </View>
        )}
        <View style={{ marginTop: spacing.md, gap: spacing.sm }}>
          <Button onPress={() => console.log("send to retailer")}>{tCommon("actions.sendToRetailer")}</Button>
          <Button variant="secondary" onPress={() => console.log("share list")}>{tCommon("actions.shareList")}</Button>
        </View>
      </Card>
    </Screen>
  );
}
