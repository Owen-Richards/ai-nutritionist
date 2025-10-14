import { Redirect } from "expo-router";

export default function QuickLog() {
  return <Redirect href="/(tabs)/track?quick=true" />;
}
