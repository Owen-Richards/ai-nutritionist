import React from "react";
import { render, RenderOptions } from "@testing-library/react-native";

import { ThemeProvider } from "@/providers/ThemeProvider";

const Providers: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

export const renderWithProviders = (ui: React.ReactElement, options?: RenderOptions) =>
  render(ui, { wrapper: Providers, ...options });
