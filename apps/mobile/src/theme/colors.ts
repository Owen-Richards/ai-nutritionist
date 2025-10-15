export type ColorPalette = {
  background: string;
  surface: string;
  surfaceElevated: string;
  primary: string;
  primaryMuted: string;
  text: string;
  textMuted: string;
  border: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
  skeletonBase: string;
  skeletonHighlight: string;
};

export const lightColors: ColorPalette = {
  background: "#f8fafc",
  surface: "#ffffff",
  surfaceElevated: "#eef2ff",
  primary: "#2563eb",
  primaryMuted: "#93c5fd",
  text: "#0f172a",
  textMuted: "#475569",
  border: "#e2e8f0",
  success: "#15803d",
  warning: "#f59e0b",
  danger: "#dc2626",
  info: "#0ea5e9",
  skeletonBase: "#e2e8f0",
  skeletonHighlight: "#f8fafc"
};

export const darkColors: ColorPalette = {
  background: "#020617",
  surface: "#0f172a",
  surfaceElevated: "#1e293b",
  primary: "#60a5fa",
  primaryMuted: "#1d4ed8",
  text: "#f8fafc",
  textMuted: "#cbd5f5",
  border: "#334155",
  success: "#4ade80",
  warning: "#fbbf24",
  danger: "#f87171",
  info: "#38bdf8",
  skeletonBase: "#1f2937",
  skeletonHighlight: "#334155"
};
