import React from "react";
import { Appearance, AppearancePreferences } from "react-native";
import { AppTheme, createTheme, ThemeMode } from "@/theme";
import { useColorScheme } from "@/hooks/useColorScheme";

const ThemeContext = React.createContext<AppTheme | null>(null);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const colorScheme = useColorScheme();
  const [mode, setMode] = React.useState<ThemeMode>(colorScheme);

  React.useEffect(() => {
    const listener = ({ colorScheme }: AppearancePreferences) => {
      if (colorScheme === "light" || colorScheme === "dark") {
        setMode(colorScheme);
      }
    };
    Appearance.addChangeListener(listener);
    return () => Appearance.removeChangeListener(listener);
  }, []);

  React.useEffect(() => {
    setMode(colorScheme);
  }, [colorScheme]);

  const theme = React.useMemo(() => createTheme(mode), [mode]);

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
};
