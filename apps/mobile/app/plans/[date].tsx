import { Redirect, useLocalSearchParams } from "expo-router";

export default function PlanByDate() {
  const { date } = useLocalSearchParams<{ date?: string }>();
  if (typeof date !== "string") {
    return <Redirect href="/(tabs)/plans" />;
  }
  return <Redirect href={`/(tabs)/plans?date=${encodeURIComponent(date)}`} />;
}
