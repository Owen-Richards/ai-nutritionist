import { Redirect } from "expo-router";

import { useAuth } from "@/providers/AuthProvider";

export default function Index() {
  const { status } = useAuth();

  if (status === "checking") {
    return null;
  }

  if (status === "authenticated") {
    return <Redirect href="/(tabs)/today" />;
  }

  return <Redirect href="/(auth)/sign-in" />;
}
