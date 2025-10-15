import { darkColors, lightColors } from "./colors";
import { radius, spacing } from "./layout";
import { typography } from "./typography";

export type AppTheme = {
  mode: "light" | "dark";
  colors: typeof lightColors;
  spacing: typeof spacing;
  radius: typeof radius;
  typography: typeof typography;
};

export const createTheme = (mode: "light" | "dark"): AppTheme => ({
  mode,
  colors: mode === "light" ? lightColors : darkColors,
  spacing,
  radius,
  typography
});

export type ThemeMode = "light" | "dark";
