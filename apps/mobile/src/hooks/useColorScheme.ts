import { useColorScheme as useNativeColorScheme } from "react-native";
import { ThemeMode } from "@/theme";

export function useColorScheme(): ThemeMode {
  const scheme = useNativeColorScheme();
  return scheme === "dark" ? "dark" : "light";
}
